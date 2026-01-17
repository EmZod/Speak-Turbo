use anyhow::{Context, Result};
use clap::Parser;
use rodio::{OutputStream, Sink, Source};
use std::collections::VecDeque;
use std::io::Read;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};

const DAEMON_URL: &str = "http://127.0.0.1:7125";
const SAMPLE_RATE: u32 = 24000;

// Buffer size: 150ms provides stable playback without perceptible latency
const MIN_BUFFER_MS: u32 = 150;
// Fade-in duration: 10ms (240 samples) eliminates startup transients
const FADE_IN_SAMPLES: usize = 240;
const MIN_BUFFER_SAMPLES: usize = (SAMPLE_RATE * MIN_BUFFER_MS / 1000) as usize;

#[derive(Parser)]
#[command(name = "speakturbo")]
#[command(about = "Ultra-fast TTS CLI")]
#[command(version)]
struct Args {
    /// Text to speak
    text: Option<String>,

    #[arg(short, long, default_value = "alba")]
    voice: String,

    #[arg(short, long)]
    output: Option<String>,

    #[arg(long)]
    list_voices: bool,
    
    /// Quiet mode - minimal output
    #[arg(short, long)]
    quiet: bool,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let start = Instant::now();

    if args.list_voices {
        println!("Voices: alba, marius, javert, jean, fantine, cosette, eponine, azelma");
        return Ok(());
    }

    let text = match args.text {
        Some(t) => t,
        None => {
            let mut buf = String::new();
            std::io::stdin().read_to_string(&mut buf)?;
            buf
        }
    };

    if text.trim().is_empty() {
        eprintln!("Error: No text");
        std::process::exit(1);
    }

    let url = format!("{}/tts?text={}&voice={}", 
        DAEMON_URL, 
        urlencoding::encode(&text),
        urlencoding::encode(&args.voice)
    );

    // Fast HTTP request
    let response = ureq::get(&url)
        .call()
        .context("Daemon not running?")?;

    if let Some(output_path) = args.output {
        let mut file = std::fs::File::create(&output_path)?;
        std::io::copy(&mut response.into_reader(), &mut file)?;
        if !args.quiet {
            eprintln!("Saved: {}", output_path);
        }
    } else {
        stream_audio(response, start, args.quiet)?;
    }

    Ok(())
}

fn stream_audio(response: ureq::Response, start: Instant, quiet: bool) -> Result<()> {
    let (_stream, stream_handle) = OutputStream::try_default()
        .context("No audio output")?;
    let sink = Sink::try_new(&stream_handle)?;

    // Lock-free-ish shared state
    let buffer = Arc::new(LockFreeBuffer::new());
    let buffer_clone = Arc::clone(&buffer);

    // Skip WAV header
    let mut reader = response.into_reader();
    let mut header = [0u8; 44];
    reader.read_exact(&mut header)?;

    // Network reader thread - HIGH PRIORITY
    let start_clone = start;
    std::thread::Builder::new()
        .name("net-reader".into())
        .spawn(move || {
            let mut chunk_buf = [0u8; 4096];
            let mut first = true;
            
            loop {
                match reader.read(&mut chunk_buf) {
                    Ok(0) => {
                        buffer_clone.set_done();
                        break;
                    }
                    Ok(n) => {
                        if first && !quiet {
                            eprintln!("⚡ {}ms", start_clone.elapsed().as_millis());
                            first = false;
                        }
                        
                        // Direct byte-to-sample conversion, no allocation
                        for chunk in chunk_buf[..n].chunks_exact(2) {
                            let sample = i16::from_le_bytes([chunk[0], chunk[1]]);
                            buffer_clone.push(sample);
                        }
                    }
                    Err(_) => {
                        buffer_clone.set_done();
                        break;
                    }
                }
            }
        })?;

    // Wait for minimal buffer
    while buffer.len() < MIN_BUFFER_SAMPLES && !buffer.is_done() {
        std::thread::sleep(Duration::from_micros(500)); // 0.5ms polling
    }

    if !quiet {
        eprintln!("▶ {}ms", start.elapsed().as_millis());
    }

    // Play!
    let source = StreamSource { buffer, samples_emitted: 0 };
    sink.append(source);
    sink.sleep_until_end();

    if !quiet {
        eprintln!("✓ {}ms", start.elapsed().as_millis());
    }

    Ok(())
}

/// Simple lock-free-ish ring buffer using atomic operations
struct LockFreeBuffer {
    data: std::sync::Mutex<VecDeque<i16>>,
    len: AtomicUsize,
    done: AtomicBool,
}

impl LockFreeBuffer {
    fn new() -> Self {
        Self {
            data: std::sync::Mutex::new(VecDeque::with_capacity(SAMPLE_RATE as usize)),
            len: AtomicUsize::new(0),
            done: AtomicBool::new(false),
        }
    }

    fn push(&self, sample: i16) {
        self.data.lock().unwrap().push_back(sample);
        self.len.fetch_add(1, Ordering::Release);
    }

    fn pop(&self) -> Option<i16> {
        let mut data = self.data.lock().unwrap();
        if let Some(s) = data.pop_front() {
            self.len.fetch_sub(1, Ordering::Release);
            Some(s)
        } else {
            None
        }
    }

    fn len(&self) -> usize {
        self.len.load(Ordering::Acquire)
    }

    fn is_done(&self) -> bool {
        self.done.load(Ordering::Acquire)
    }

    fn set_done(&self) {
        self.done.store(true, Ordering::Release);
    }
}

struct StreamSource {
    buffer: Arc<LockFreeBuffer>,
    samples_emitted: usize,
}

impl Iterator for StreamSource {
    type Item = i16;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            if let Some(sample) = self.buffer.pop() {
                // Apply fade-in to first FADE_IN_SAMPLES to eliminate startup transients
                let output = if self.samples_emitted < FADE_IN_SAMPLES {
                    let factor = self.samples_emitted as f32 / FADE_IN_SAMPLES as f32;
                    (sample as f32 * factor) as i16
                } else {
                    sample
                };
                self.samples_emitted += 1;
                return Some(output);
            }
            
            if self.buffer.is_done() {
                return None;
            }
            
            // Spin-wait (aggressive but low latency)
            std::hint::spin_loop();
        }
    }
}

impl Source for StreamSource {
    fn current_frame_len(&self) -> Option<usize> { None }
    fn channels(&self) -> u16 { 1 }
    fn sample_rate(&self) -> u32 { SAMPLE_RATE }
    fn total_duration(&self) -> Option<Duration> { None }
}

mod urlencoding {
    pub fn encode(s: &str) -> String {
        let mut r = String::with_capacity(s.len() * 2);
        for c in s.chars() {
            match c {
                'a'..='z' | 'A'..='Z' | '0'..='9' | '-' | '_' | '.' | '~' => r.push(c),
                ' ' => r.push_str("%20"),
                _ => {
                    for b in c.to_string().as_bytes() {
                        r.push_str(&format!("%{:02X}", b));
                    }
                }
            }
        }
        r
    }
}
