/**
 * AudioWorkletProcessor — real-time PCM capture.
 *
 * Runs in a dedicated audio thread. Accumulates Float32 samples
 * from the browser's audio graph, converts to Int16 PCM every ~100ms
 * (1600 samples @ 16kHz), and posts the buffer to the main thread.
 *
 * Target sample rate: 16000 Hz (set when creating AudioContext).
 * Frame size: 128 samples per process() call (browser standard).
 * Batch size: 1600 samples = 100ms @ 16kHz (12-13 process() calls).
 */

const BATCH_SAMPLES = 1600; // 100ms at 16kHz

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(BATCH_SAMPLES);
    this._offset = 0;
    this._active = true;

    this.port.onmessage = (event) => {
      if (event.data === 'stop') {
        this._active = false;
      }
    };
  }

  process(inputs) {
    if (!this._active) return false;

    const input = inputs[0];
    if (!input || !input[0]) return true;

    const channelData = input[0]; // mono

    for (let i = 0; i < channelData.length; i++) {
      this._buffer[this._offset++] = channelData[i];

      if (this._offset >= BATCH_SAMPLES) {
        // Convert Float32 → Int16 PCM
        const pcm = new Int16Array(BATCH_SAMPLES);
        for (let j = 0; j < BATCH_SAMPLES; j++) {
          const clamped = Math.max(-1, Math.min(1, this._buffer[j]));
          pcm[j] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
        }
        // Transfer ownership (zero-copy) to main thread
        this.port.postMessage({ type: 'pcm', buffer: pcm.buffer }, [pcm.buffer]);
        this._offset = 0;
      }
    }

    return true;
  }
}

registerProcessor('audio-processor', AudioProcessor);
