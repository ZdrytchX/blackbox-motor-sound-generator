# --- HOW TO USE FOR DUMMIES ---
# Step 1: Betaflight Blackbox Explorer / Configurator: Select your log and export as CSV
# Step 2: Dump them in the same folder as this file. Right click "Raw" and "Save As" to download to your pc. You can edit .py files with notepad
# Step 3: Install python 3 if you haven't done so yet
# Step 4: pip install scipy etc. as needed
# Step 5: python.exe [thisfile].py or py [thisfile].py
# Step 6: Profit?!?
# Step 7: If it sounds bad, adjust OVERTONE_WEIGHTS and run this file again
# 
# Please note that eRPM reported values isn't the real RPM, there's some scalar involved
# 
# No warranty provided for you bricking your own system out of your own stupidity whatever blah blah
# 
#   DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#   Version 2, December 2004 
#
# Copyright (C) 2004 Sam Hocevar <sam@hocevar.net> 
#
# Everyone is permitted to copy and distribute verbatim or modified 
# copies of this license document, and changing it is allowed as long 
# as the name is changed. 

#   DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE 
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION 
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.

import glob
import os
import numpy as np
from scipy.io import wavfile
from scipy.integrate import cumulative_trapezoid

# --- Configuration & Audio Settings ---
SAMPLE_RATE = 44100         # Standard 44.1 kHz audio rate
POLES = 12                  # 12-pole motor (12P / 6 pole pairs)
ATTENUATION = 0.5           # Master volume scaling
ERPM_SCALE_FACTOR = 52.0    # Multiplier applied to base eRPM signal
NOISE_HZ = 220              # additional averaged noise

# Motor & Propeller Sine Harmonics
OVERTONE_WEIGHTS = {
    3: 0.375,   # BPF Base / 3-blade prop harmonic
    6: 0.25,    # 2nd BPF Harmonic
    9: 0.1875,  # 3rd BPF Harmonic
    12: 0.125,  # 12-pole switching harmonic
    36: 0.0625  # ESC switching frequency harmonic
}

def parse_csv_or_text_log(file_path):
    """
    Parses decoded Betaflight CSV/TXT exports, handling header metadata and multiple sessions.
    """
    parsed_logs = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]

    i = 0
    log_id = 1
    
    while i < len(lines):
        if '"time"' in lines[i].lower() or 'loopiteration' in lines[i].lower():
            headers = [h.strip(' "') for h in lines[i].split(',')]
            i += 1
            data_rows = []
            
            while i < len(lines):
                line = lines[i]
                if line.startswith('"Product"') or line.startswith('"firmware"') or '"loopiteration"' in line.lower():
                    break
                    
                parts = [p.strip(' "') for p in line.split(',')]
                if len(parts) == len(headers):
                    try:
                        data_rows.append([float(p) if (p != '' and p.lower() != 'nan') else 0.0 for p in parts])
                    except ValueError:
                        pass
                i += 1
            
            if data_rows:
                parsed_logs.append({
                    'log_id': log_id,
                    'headers': headers,
                    'data': np.array(data_rows, dtype=float)
                })
                log_id += 1
        else:
            i += 1

    if not parsed_logs:
        print(f"  [!] Skipping {file_path}: No data rows found following header.")

    return parsed_logs

def generate_tone(audio_time, frequencies):
    """
    Generates a phase-continuous sine wave by cumulative integration over the audio timeline.
    """
    phase = 2.0 * np.pi * cumulative_trapezoid(frequencies, audio_time, initial=0.0)
    return np.sin(phase)

def generate_motor_sound(audio_time, fundamental_freqs, volume_envelope):
    """
    Synth fundamentals and each harmonic
    """
    motor_signal = generate_tone(audio_time, fundamental_freqs) * 0.25
    
    for mult, weight in OVERTONE_WEIGHTS.items():
        overtone_signal = generate_tone(audio_time, fundamental_freqs * mult)
        motor_signal += overtone_signal * weight
        
    return motor_signal * volume_envelope

def generate_additional_noise(audio_time, avg_throttle, gyro_total):
    """
    Generates throttle-linked sine wave air flutter.
    """
    # Sine Pitch Sweep
    additional_noise = (avg_throttle ** 1.2) * NOISE_HZ
    
    raw_sine = generate_tone(audio_time, additional_noise)
    
    # Scale sine volume dynamically with throttle & gyro intensity
    sine_vol = (avg_throttle ** 2) * 0.03125 + (gyro_total * 0.000002)
    sine_vol = np.clip(sine_vol, 0.0, 0.0625)
    
    return raw_sine * sine_vol

def process_log_to_audio(log_data, output_filename):
    headers = log_data['headers']
    data = log_data['data']

    # Extract time column
    time_col = None
    for candidate in ['time', 'time (us)', 'Time']:
        if candidate in headers:
            time_col = candidate
            break

    if not time_col:
        print(f"  [!] Could not find 'time' header in log.")
        return

    time_idx = headers.index(time_col)
    time_sec = data[:, time_idx] / 1e6
    time_sec = time_sec - time_sec[0]

    duration = time_sec[-1]
    if duration <= 0:
        print(f"  [!] Skipping {output_filename}: Invalid log duration ({duration:.2f}s).")
        return

    num_audio_samples = int(duration * SAMPLE_RATE)
    audio_time = np.linspace(0, duration, num_audio_samples)

    def resample_signal(col_name, default_val=0.0):
        if col_name in headers:
            col_idx = headers.index(col_name)
            return np.interp(audio_time, time_sec, data[:, col_idx])
        return np.full_like(audio_time, default_val)

    # Extract Gyro Signals
    raw_gyro_x = resample_signal('gyroADC[0]', 0.0)
    raw_gyro_y = resample_signal('gyroADC[1]', 0.0)
    raw_gyro_z = resample_signal('gyroADC[2]', 0.0)

    gyro_x_factor = 1.0 + (raw_gyro_x * 0.00005)
    gyro_y_factor = 1.0 + (raw_gyro_y * 0.00005)
    gyro_total = np.abs(raw_gyro_x) + np.abs(raw_gyro_y) + np.abs(raw_gyro_z)

    # Process Motor Signals
    motor_freqs = []
    motor_volumes = []
    throttles = []

    # eRPM = DSHOT telemetry reported motor RPM (not accurate at the top end of power curve)
    # motor = PID sum output to motors, always comes before eRPM so we use this for motor strain intensity and thus volume
    for i in range(4):
        motor_raw = resample_signal(f'motor[{i}]', default_val=1000.0)
        throttle = np.clip((motor_raw - 1000.0) / 1000.0, 0.0, 1.0)
        throttles.append(throttle)
        
        volume_env = np.clip(0.0625 + 0.9375 * throttle, 0.0625, 1.0)
        motor_volumes.append(volume_env)

        # Base eRPM values multiplied by scale factor
        erpm = resample_signal(f'eRPM[{i}]', default_val=0.0) * ERPM_SCALE_FACTOR
        if np.max(erpm) > 0:
            mech_hz = (erpm / (POLES / 2.0)) / 60.0
        else:
            mech_hz = 30.0 + (throttle ** 1.5) * 1170.0

        # Differential gyro pitch shifts across quad quadrants (X = Pitch, Y = Roll)
        if i in [2, 3]:  # Motors 3, 4 (Front)
            mech_hz *= gyro_x_factor
        else:            # Motors 1, 2 (Rear)
            mech_hz /= gyro_x_factor

        if i in [1, 2]:  # Motors 2, 3 (Left)
            mech_hz *= gyro_y_factor
        else:            # Motors 1, 4 (Right)
            mech_hz /= gyro_y_factor

        motor_freqs.append(mech_hz)

    # Synthesize Motors individually
    m1_right = generate_motor_sound(audio_time, motor_freqs[0], motor_volumes[0])
    m2_right = generate_motor_sound(audio_time, motor_freqs[1], motor_volumes[1])
    m3_left  = generate_motor_sound(audio_time, motor_freqs[2], motor_volumes[2])
    m4_left  = generate_motor_sound(audio_time, motor_freqs[3], motor_volumes[3])

    left_base = m3_left + m4_left
    right_base = m1_right + m2_right

    # Additional Noise Generator based on averaged throttle
    avg_throttle = np.mean(throttles, axis=0)
    sine_flutter = generate_additional_noise(audio_time, avg_throttle, gyro_total)

    # Dynamic Stereo Panning / Wobble driven by Gyro Z (Yaw rate)
    pan_shift = np.clip(raw_gyro_z * -0.00025, -0.4, 0.4)
    
    left_bleed = np.clip(-pan_shift, 0.0, 0.4)
    right_bleed = np.clip(pan_shift, 0.0, 0.4)

    left_channel = (1.0 - right_bleed) * left_base + left_bleed * right_base + sine_flutter
    right_channel = (1.0 - left_bleed) * right_base + right_bleed * left_base + sine_flutter

    stereo_signal = np.vstack((left_channel, right_channel)).T

    # Peak Normalization
    max_val = np.max(np.abs(stereo_signal))
    if max_val > 0:
        stereo_signal = stereo_signal / max_val

    # 20ms fade-in/fade-out
    fade_samples = min(int(SAMPLE_RATE * 0.02), num_audio_samples // 2)
    if fade_samples > 0:
        fade_in = np.linspace(0.0, 1.0, fade_samples)[:, np.newaxis]
        fade_out = np.linspace(1.0, 0.0, fade_samples)[:, np.newaxis]
        stereo_signal[:fade_samples] *= fade_in
        stereo_signal[-fade_samples:] *= fade_out

    audio_int16 = (stereo_signal * 32767 * ATTENUATION).astype(np.int16)
    wavfile.write(output_filename, SAMPLE_RATE, audio_int16)
    print(f"  [+] Saved audio file: {output_filename}")

def main():
    log_files = glob.glob("*.csv") + glob.glob("*.txt")
    
    if not log_files:
        print("No .csv or .txt blackbox log files found in the working directory.")
        return

    for file_path in log_files:
        print(f"\nProcessing file: {file_path}")
        logs = parse_csv_or_text_log(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        for log in logs:
            out_name = f"{base_name}_log{log['log_id']}_audio.wav"
            process_log_to_audio(log, out_name)

if __name__ == "__main__":
    main()
