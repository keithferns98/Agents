import cv2
import numpy as np

def process_video(input_path, output_path):
    cap = cv2.VideoCapture(input_path)
    
    # Get video properties
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    
    # Target the top 15%
    roi_height = int(height * 0.15)
    
    # Define Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Create a mask for the top 15%
        # If the watermark is white text, we can auto-detect it here
        roi = frame[0:roi_height, 0:width]
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Detect bright pixels (watermark) in the top 15%
        _, mask = cv2.threshold(gray_roi, 200, 255, cv2.THRESH_BINARY)
        
        # 2. Inpaint only the detected watermark area
        inpainted_roi = cv2.inpaint(roi, mask, 3, cv2.INPAINT_TELEA)
        
        # 3. Put the cleaned ROI back into the frame
        frame[0:roi_height, 0:width] = inpainted_roi
        
        out.write(frame)

    cap.release()
    out.release()

# process_video('videos/input.mp4', 'output_cleaned.mp4')

import subprocess

import subprocess
import shlex

def clean_video(input_file, output_file="ffmpeg_cleaned_output.mp4"):
    # Using a complex filter: 
    # 1. Crop the top 15% (h=ih*0.15)
    # 2. Apply a heavy blur to that cropped section
    # 3. Overlay that blurred strip back onto the original video
    # This avoids the 'band' error and handles vertical video perfectly.
    
    filter_logic = (
        "[0:v]crop=iw:ih*0.15:0:0,boxblur=10:5[fg];"
        "[0:v][fg]overlay=0:0"
    )

    command = [
        'ffmpeg',
        '-i', input_file,
        '-filter_complex', filter_logic,
        '-c:a', 'copy',  # Keep the audio!
        '-y',             # Overwrite output file if it exists
        output_file
    ]

    try:
        # We use a list instead of a string + shell=True for better stability on Windows
        subprocess.run(command, check=True)
        print(f"Success! Cleaned video saved as: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

# Run the function
# clean_video("videos/input.mp4")

import cv2
import easyocr
import numpy as np
import subprocess

def remove_watermark_persistent(input_video, target_text, output_video):
    reader = easyocr.Reader(['en'])
    cap = cv2.VideoCapture(input_video)
    
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    roi_h  = int(height * 0.15)
    
    found_coords = None
    
    # --- PASS 1: DEEP SCAN ---
    print("Searching for watermark location (Deep Scan)...")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # We check the video at 0%, 25%, 50%, and 75% to make sure we find it
    check_points = [0, total_frames//4, total_frames//2, (3*total_frames)//4]
    
    for point in check_points:
        cap.set(cv2.CAP_PROP_POS_FRAMES, point)
        ret, frame = cap.read()
        if not ret: continue
        
        roi = frame[0:roi_h, 0:width]
        results = reader.readtext(roi)
        for (bbox, text, prob) in results:
            if target_text.lower() in text.lower():
                x1 = int(bbox[0][0]) - 110 # Extra buffer for emoji
                y1 = int(bbox[0][1]) - 10
                x2 = int(bbox[2][0]) + 15
                y2 = int(bbox[2][1]) + 10
                found_coords = (max(0, x1), max(0, y1), min(width, x2), min(roi_h, y2))
                break
        if found_coords: break

    if not found_coords:
        # FALLBACK: If OCR fails, we use a standard guess for invideo watermarks
        print("OCR failed to find text. Using fallback coordinates for top-left...")
        found_coords = (20, 40, 450, 120) 

    # --- PASS 2: REWIND AND CLEAN EVERY FRAME ---
    print(f"Cleaning all frames using lock: {found_coords}")
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_avi = "temp_locked_clean.mp4"
    out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))

    x1, y1, x2, y2 = found_coords

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # We create a mask for that specific area EVERY frame
        # We don't check for white pixels anymore; we just heal that spot
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
        
        # Inpaint
        frame = cv2.inpaint(frame, mask, 5, cv2.INPAINT_TELEA)
        out.write(frame)

    cap.release()
    out.release()

    # --- FINAL PASS: AUDIO ---
    subprocess.run(f'ffmpeg -i "{temp_avi}" -i "{input_video}" -map 0:v -map 1:a -c:v libx264 -crf 18 -c:a copy "{output_video}" -y', shell=True)
    print("Done! Check final_output.mp4")

# remove_watermark_persistent("videos/input.mp4", "keith", "final_output_v2.mp4")

import cv2
import easyocr
import numpy as np
import subprocess

def remove_watermarks_final(input_video, top_text, bottom_text, output_video):
    reader = easyocr.Reader(['en'])
    cap = cv2.VideoCapture(input_video)
    
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS)
    
    top_coords = None
    bottom_coords = None

    # --- PASS 1: AGGRESSIVE SCAN ---
    print("Scanning for watermark anchors...")
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Check more points to ensure we catch Storyblocks when it appears
    check_points = np.linspace(0, total_frames-1, 10, dtype=int)

    for point in check_points:
        cap.set(cv2.CAP_PROP_POS_FRAMES, point)
        ret, frame = cap.read()
        if not ret: continue
        
        # Scan TOP (Invideo)
        if not top_coords:
            roi_top = frame[0:int(height*0.20), 0:width]
            res_top = reader.readtext(roi_top)
            for (bbox, text, prob) in res_top:
                if top_text.lower() in text.lower():
                    # x1, y1, x2, y2 with extra padding for emoji/glow
                    x1, y1 = int(bbox[0][0]) - 120, int(bbox[0][1]) - 15
                    x2, y2 = int(bbox[2][0]) + 20, int(bbox[2][1]) + 15
                    top_coords = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
                    break

        # Scan BOTTOM (Storyblocks)
        if not bottom_coords:
            roi_bot = frame[int(height*0.75):height, 0:width]
            res_bot = reader.readtext(roi_bot)
            for (bbox, text, prob) in res_bot:
                if bottom_text.lower() in text.lower():
                    offset = int(height*0.75)
                    # Bottom watermarks often have wider spacing
                    x1, y1 = int(bbox[0][0]) - 30, int(bbox[0][1]) + offset - 15
                    x2, y2 = int(bbox[2][0]) + 30, int(bbox[2][1]) + offset + 15
                    bottom_coords = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
                    break

    # --- PASS 2: FORCED HEALING ---
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    temp_avi = "temp_final_processing.mp4"
    out = cv2.VideoWriter(temp_avi, fourcc, fps, (width, height))

    print(f"Top Mask: {top_coords}")
    print(f"Bottom Mask: {bottom_coords}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # We create the mask for EVERY frame, even if the watermark isn't visible
        # This prevents the "blinking" or "missing frames" issue
        mask = np.zeros(frame.shape[:2], dtype=np.uint8)
        
        if top_coords:
            cv2.rectangle(mask, (top_coords[0], top_coords[1]), (top_coords[2], top_coords[3]), 255, -1)
        
        if bottom_coords:
            cv2.rectangle(mask, (bottom_coords[0], bottom_coords[1]), (bottom_coords[2], bottom_coords[3]), 255, -1)
        
        # Increase inpaint radius to 7 for smoother blending
        frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        out.write(frame)

    cap.release()
    out.release()

    # --- FINAL: STITCH AUDIO ---
    cmd = f'ffmpeg -i "{temp_avi}" -i "{input_video}" -map 0:v -map 1:a -c:v libx264 -crf 18 -c:a copy "{output_video}" -y'
    subprocess.run(cmd, shell=True)
    print("Done! Both watermarks should now be completely gone.")

# Execute
remove_watermarks_final("videos/input.mp4", "invideo/keith", "storyblocks", "cleaned_final.mp4")