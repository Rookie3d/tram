import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/..')

import torch
import argparse
import numpy as np
from glob import glob
from pycocotools import mask as masktool

from lib.pipeline import video2frames, detect_segment_track
from lib.camera import run_metric_slam, calibrate_intrinsics, align_cam_to_world


parser = argparse.ArgumentParser()
parser.add_argument("--img_folder", type=str, default='./example_video.mov', help='input folder')
parser.add_argument("--static_camera", action='store_true', help='whether the camera is static')
parser.add_argument("--visualize_mask", action='store_true', help='save deva vos for visualization')
parser.add_argument("--output_folder", type=str, default='./example_video.mov', help='output')
args = parser.parse_args()


seq_folder = args.output_folder
img_folder = args.img_folder
os.makedirs(seq_folder, exist_ok=True)
os.makedirs(img_folder, exist_ok=True)

##### Extract Frames #####
#print('Extracting frames ...')
#nframes = video2frames(file, img_folder)

##### Detection + SAM + DEVA-Track-Anything #####
print('Detect, Segment, and Track ...')
imgfiles = sorted(glob(f'{img_folder}/*.jpg')+glob(f'{img_folder}/*.png'))
boxes_, masks_, tracks_ = detect_segment_track(imgfiles, seq_folder, thresh=0.25, 
                                               min_size=100, save_vos=args.visualize_mask)

##### Run Masked DROID-SLAM #####
print('Masked Metric SLAM ...')
masks = np.array([masktool.decode(m) for m in masks_])
masks = torch.from_numpy(masks)

cam_int, is_static = calibrate_intrinsics(img_folder, masks, is_static=args.static_camera)
cam_R, cam_T = run_metric_slam(img_folder, masks=masks, calib=cam_int, is_static=is_static)
wd_cam_R, wd_cam_T, spec_f = align_cam_to_world(imgfiles[0], cam_R, cam_T)

camera = {'pred_cam_R': cam_R.numpy(), 'pred_cam_T': cam_T.numpy(), 
          'world_cam_R': wd_cam_R.numpy(), 'world_cam_T': wd_cam_T.numpy(),
          'img_focal': cam_int[0], 'img_center': cam_int[2:], 'spec_focal': spec_f}

np.save(f'{seq_folder}/camera.npy', camera)
np.save(f'{seq_folder}/boxes.npy', boxes_)
np.save(f'{seq_folder}/masks.npy', masks_)
np.save(f'{seq_folder}/tracks.npy', tracks_)

