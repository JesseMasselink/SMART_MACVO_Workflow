# MACVO Evaluation

## Introduction

This repository contains the implementation and evaluation of the MAC-VO algorithm on datasets recorded using a ZED stereo camera and NVIDIA Jetson platform, using ROS2. This work was done during an internship focused on comparing visual-inertial odometry (VIO) systems for robust and trustworthy pose estimation.

## Overview

MAC-VO (Metrics-Aware Covariance for Learning-based Visual Odometry) improves stereo VO by:
- Estimating keypoint-wise uncertainty using a transformer-based flow estimation network.
- Filtering out unreliable points before estimating 3D motion.
- Computing pose using weighted 3D keypoints.

Full paper: [arxiv.org/pdf/2409.09479v2](https://arxiv.org/pdf/2409.09479v2)

## Dependencies

### System
- **Platform:** NVIDIA Jetson (Jetpack 6.0)
- **CUDA:** 12.2
- **Python:** 3.10+
- **ROS2:** Humble

### Python (virtual environment recommended)
```bash
pip install -r requirements.txt
```
Torch version: Must match Jetson/CUDA compatibility. See Troubleshooting for notes.


## ZED Camera Setup
Install from: https://www.stereolabs.com/en-nl/developers/release

ROS2 Wrapper: https://github.com/stereolabs/zed-ros2-wrapper

Run with:

```bash
ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zed2
```


## Installation guide

### Create MACVO environment
#### ROS2 Wrapper
Navigate to MACVO's ROS2 Wrapper repository https://github.com/MAC-VO/MAC-VO-ROS2

Fork MACVO's ROS2 wrapper repository in your ROS2 workspace
```bash
git clone https://github.com/MAC-VO/MAC-VO-ROS2.git
```

#### MACVO
Inside the ROS2 wrapper, navigate to /MACVO_ROS2/src

Clone original MACVO files into src file
```bash
git clone https://github.com/MAC-VO/MAC-VO.git
```

### Create & Activate Virtual Environment
```bash
cd /path/to/MACVO_ROS2
python3 -m venv macvo_venv
source macvo_venv/bin/activate
```

### Install Requirements
Install macvo requirements trough pip with included document:
```bash
pip install -r macvo_venv_requirements.txt
```

### Include pretrained model
MACVO needs a trained model to perform the algorithm. 
This file can be found in the used NVIDIA Jetson's temp folder (/home/sarax/temp)
Or MACVO's release page: https://github.com/MAC-VO/MAC-VO/releases/tag/model

Create a new folder called 'Model' in the root ROS2 wrapper directory and put the pretrained models in the folder.
```bash
$ mkdir Model
$ wget -O Model/MACVO_FrontendCov.pth https://github.com/MAC-VO/MAC-VO/releases/download/model/MACVO_FrontendCov.pth
$ wget -O Model/MACVO_posenet.pkl https://github.com/MAC-VO/MAC-VO/releases/download/model/MACVO_posenet.pkl
```

### Configuration and Code Modifications
To ensure MAC-VO operates correctly with your ZED stereo camera and publishes valid ROS2 topics, a few key changes must be made to the configuration and wrapper code.

#### Edit Configuration file
Navigate to 
```bash
/MAC-VO-ROS2/MACVO_ROS2/config/zedcam_macvo.yaml
```

Then either:
- Option A: replace this file with the zedcam_macvo.yaml from this repo's /changed_files,
- Option B: Manually update the camera parameters at the bottom of the file to match the values from the /camera_info topic in your recorded bag file.
    See the Attachments for the exact parameters and further explanation.


#### Modify MACVO.py (ROS2 Wrapper)
Navigate to the ROS2 wrapper MACVO.py 
```bash
/MAC-VO-ROS2/MACVO_ROS2/MACVO.py
```
Important: Do not confuse with original MACVO.py at
```bash
/MAC-VO-ROS2/MACVO_ROS2/src/MACVO.py
```

Then either:
- Option A: Replace the wrapper script with the updated MACVO.py from the /changed_files directory in this repository.
- Option B: Manually update the publish_data() function to ensure the timestamps are generated using the current ROS2 clock time (to fix the alignment issue with evo_traj).
    A detailed explanation of the fix can be found in the Attachments.


## Running the System
Note: Building the ROS2 MACVO wrapper as a standard ROS2 package caused unresolved errors during development (see Attachments for details). 
As a workaround, the system can be executed by running the MACVO.py script directly from the ROS2 wrapper.

To ensure that all data from the dataset is correctly processed by MACVO and recorded into a new bag file, follow this sequence:

### 1. Running MACVO on a Dataset
Remember, this is the ROS2 wrapper MACVO.py file.

To run the MACVO algorithm with zedcam config:
```bash
cd /path/to/MAC-VO-ROS2/MACVO_ROS2/
python3 MACVO.py --config /config/zedcam_macvo.yaml
```
Make sure that the YAML configuration file (zedcam_macvo.yaml) contains correct camera parameters, which can be extracted from the /camera_info topic in the bag file (explained earlier).

### 2. Recording MACVO Output
While the bag file is playing and MACVO.py is running, the following topics will be published:
- /macvo/pose
- /macvo/map
- /zed/zed_node/odom
- /Rotbot_1/pose (from OptiTrack ground truth, if applicable)

To record these topics into a new ROS2 bag file:
```bash
ros2 bag record /macvo/pose /macvo/map /zed/zed_node/odom /Robot_1/pose
```
Modify the list of topics to match the available or relevant data in your specific bag file.

### 3. Playing Dataset Bagfile
Once MACVO is initialized and topics are registered for recording, play the dataset bagfile at a reduced rate (0.2) to allow sufficient processing time:
```bash
ros2 bag play /path/to/datset_bagfile -r 0.2
```
Important: Starting the bagfile playback before MACVO is fully initialized may result in missed data or misaligned timestamps.


## Evaluation with EVO
To evaluate the recorded output results with EVO, some preperation steps are nessasary.

### Bagfile Timestamp Alignment Tool: align_bag_timestamps.py
In ROS2 recordings, timestamp misalignment can occur when some topics (like /macvo/pose) are published after computational delays, while others (like /Robot_1/pose) are recorded in real-time. This mismatch causes issues when comparing trajectories using tools like evo_traj.

To fix this, the align_bag_timestamps.py script updates each message’s header.stamp to match its actual bagfile timestamp, ensuring all topics are time-aligned for accurate evaluation.

#### What the script does:
- Opens a recorded ROS2 bag file.
- Reads all messages and updates the header.stamp field of each message to match the recorded bag timestamp.
- Writes the corrected messages to a new bag file.
- Ensures compatibility with evo_traj, which depends on accurate timestamp alignment for multi-trajectory evaluation.

#### Usage
```bash
python3 align_bag_timestamps.py \
  --input-bag /path/to/original_bag \
  --output-bag /path/to/fixed_bag \
  --ref-topic /Robot_1/pose \
  --shift-topics /macvo/pose /macvo/map /zed/zed_node/odom
```
- --input-bag: The location of the bagfile that needs realignment
- --output-bag: The location of the aligned bagfile, with new filename
- --ref-topic: The trusted, real-time recorded topic (OptiTrack ground truth).
- --shift-topics: The topics to realign based on the reference.
Internally, this script sets each header.stamp to the time at which the message was actually recorded by ROS2, preserving chronological consistency across all topics.

### Installing EVO
For installation tutorials and guidelines, see EVO repository: https://github.com/MichaelGrupp/evo


### Plotting Trajectory using ROS2 Bagfile:
To plot the trajectories of the recorded topics using EVO:
```bash
evo_traj bag2 /path/to/aligned/bag_dir /macvo/pose /zed/zed_node/odom --ref /Robot_1/pose -a -p
```
- 

Important: Timestamps of recorded topics must be aligned.

### Plotting Results using ROS2 Bagfile
To plot the results of the recorded topics using EVO:
```bash
evo_ape bag2 /path/to/aligned/bag_dir /Robot_1/pose /macvo/pose /zed/zed_node/odom -va --plot --save_results ape_results.zip
```
- /Robot_1/pose is the ground truth
- /macvo/pose is the estimated trajectory by MACVO
- /zed/zed_node/odom is the estimated trajectory by ZED camera
- -v = verbose output
- -a = alignment (rigid body alignment with scale correction if needed)
- --plot = show ATE plot
- --save_results = save the results to a .zip file

### If torch or CUDA fails:
See Troubleshooting


## Troubleshooting

### Wrong Torch version (CPU-only):
If you encounter errors from PyTorch or see that torch.cuda.is_available() returns False, it’s likely that a CPU-only version of PyTorch was installed by default. On Jetson devices, this is a common issue because PyTorch needs to be compiled specifically for JetPack and CUDA compatibility.

1. Uninstall all existing PyTorch installations:
```bash
pip uninstall torch -y
pip uninstall torchvision -y
pip uninstall torchaudio -y
```
2. Download Jetson-compatible PyTorch wheels:
Go to the official NVIDIA forums or use this Jetson PyTorch installation guide to download wheels compatible with your JetPack and CUDA version (JetPack 6.0 → CUDA 12.2).

3. Install the correct versions manually:
```bash
pip install /path/to/torch-<version>-cp310-cp310-linux_aarch64.whl
pip install /path/to/torchvision-<version>-cp310-cp310-linux_aarch64.whl
pip install /path/to/torchaudio-<version>-cp310-cp310-linux_aarch64.whl
```

4. Verify installation:
Run the following command to confirm that PyTorch is using CUDA:
```bash
python3 -c "import torch; print(torch.__version__, torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```
This should then output:
```bash
2.3.0 True
NVIDIA Orin
```

### ROS2 not using venv Python:
During setup, ROS2 may default to the system-wide Python installation instead of the virtual environment. This can lead to missing dependencies or incompatibilities—especially with packages like torch.

To ensure ROS2 and your virtual environment are correctly synchronized, follow these steps:
```bash
# Activate your virtual environment
source /path/to/your/venv/bin/activate

# Source the ROS2 setup script *after* activating the venv
source /opt/ros/humble/setup.bash
```
This order matters: Activating the virtual environment first ensures that python3, pip, and all Python modules come from your venv, while sourcing ROS2 ensures the ROS environment variables and tools are available.

You can confirm it's working by checking:
```bash
which python3
# Should return a path inside your virtual environment

which colcon
# Should also return a path inside the venv (if installed there)
```

If colcon is still not detected from the venv, try symlinking it:
```bash
ln -s /usr/bin/colcon /path/to/your/venv/bin/colcon
```

### PyQt5 Instalation Issue on NVIDIA Jetson (Unsolvable)
When attempting to use evo_traj for visualizing trajectories, you may encounter errors related to PyQt5 not being installed on NVIDIA Jetson devices. Despite repeated installation attempts, PyQt5 fails to install or run properly.

#### Root Cause:
Jetson devices (especially with JetPack 6.0) often face compatibility issues with GUI frameworks like PyQt5 due to:
- ARM architecture limitations (many Python wheels are not compiled for aarch64).
- Dependency conflicts with Jetson's CUDA libraries and Python environment.
- Lack of official support for some GUI libraries on embedded Linux.

#### Resolution:
This issue is unfixable on Jetson platforms due to architectural constraints. The workaround is to:
- Transfer the recorded bag files to a desktop/laptop machine (x86_64 architecture).
- Perform trajectory visualization with evo_traj on that machine, where PyQt5 can be installed without issues.



- Evaluation performed using EVO plots.
