# Orange Pi 5 – Baseline & Current Status

**Project:** Industrial Worker Safety Monitoring / PPE Non-compliance Detection  
**Board role:** Edge AI deployment target  
**Last updated:** 2026-09-18

---

## 1. Purpose

This file records the current hardware/software baseline of the Orange Pi 5 and the work already completed.

Main goal:

```text
OV13855 Camera
    ↓
Linux / V4L2 / RKISP
    ↓
Pre-processing
    ↓
RKNN Runtime
    ↓
RK3588S NPU
    ↓
PPE Detection / Person–PPE Association
    ↓
Benchmark + Application Integration
```

Current status: **OS + network + remote access + camera bring-up are working. AI/NPU deployment is the next phase.**

---

## 2. Hardware Baseline

| Item | Current baseline |
|---|---|
| Board | Orange Pi 5 (original version) |
| SoC | Rockchip RK3588S |
| CPU architecture | ARM64 / aarch64 |
| RAM | 4 GB |
| Boot storage | microSD |
| microSD detected size | ~29.7 GB usable (~32 GB card) |
| SPI Flash | 16 MB |
| Onboard eMMC | Not available on this Orange Pi 5 version |
| Onboard Wi-Fi | Not available |
| Camera | OV13855, 13 MP, MIPI CSI |
| Camera connector in use | Camera3 |
| Display | HDMI tested successfully; no longer required for normal SSH work |

### Storage note

The lack of eMMC does **not** block AI deployment.

The `.rknn` model is loaded from storage into RAM and inference runs on the NPU. microSD mainly affects boot/package install/model loading/file I/O, not steady-state NPU inference FPS.

NVMe can be considered later if higher storage performance or endurance is needed.

---

## 3. OS Baseline

| Item | Value |
|---|---|
| Image | Orange Pi Ubuntu Jammy Desktop XFCE |
| Orange Pi image version | 1.2.4 |
| Ubuntu | 22.04.5 LTS (Jammy) |
| Kernel | `6.1.99-rockchip-rk3588` |
| Architecture | `aarch64` |
| Root filesystem | ext4 |
| Root device | `/dev/mmcblk1p1` |
| Root filesystem size | ~29 GB |
| RAM visible to Linux | ~3.8 GiB |
| Swap | ~1.9 GiB |

The system successfully boots from microSD.

### Important baseline rule

For now, **do not run a full `apt upgrade`** unless there is a specific reason.

Reason: the current Orange Pi vendor kernel/driver stack is known to work with the OV13855 + Rockchip camera pipeline, so we want to avoid changing the kernel/driver baseline unexpectedly.

---

## 4. Camera Bring-up Status

Camera bring-up is considered **DONE** for the current baseline.

### 4.1 Sensor detection

OV13855 is detected correctly:

```text
ov13855 2-0036: Detected OV00d855 sensor, REVISION 0xb0
```

Sensor mode observed:

```text
4224x3136
RAW10 / SBGGR10
30 FPS
```

### 4.2 Camera data path

Current working path:

```text
OV13855
    ↓
MIPI CSI / DPHY
    ↓
RKCIF
    ↓
RKISP
    ↓
rkisp_mainpath
    ↓
/dev/video11
```

Important nodes:

```text
/dev/media0   -> RKCIF media graph
/dev/media1   -> RKISP media graph
/dev/video11  -> rkisp_mainpath
/dev/video-camera0 -> /dev/video11
```

### 4.3 ISP/capture formats

`/dev/video11` supports formats including:

```text
UYVY
NV16
NV61
NV21
NV12
NM21
NM12
```

Supported size range is stepwise up to:

```text
4224x3136
```

### 4.4 Verified working capture profile

Current verified profile:

```text
Resolution : 1920x1080
Format     : NV12
Frame size : 3,110,400 bytes
FPS        : ~29.95
```

Test performed:

```text
300 consecutive frames
~33.38 ms/frame
~29.95 FPS
No serious timeout/drop error observed
```

A single frame was also captured successfully:

```text
frame_1080p.nv12
~3.0 MiB
```

### 4.5 Live preview

Live camera preview with GStreamer was tested successfully:

```bash
gst-launch-1.0 \
  v4l2src device=/dev/video11 \
  ! video/x-raw,format=NV12,width=1920,height=1080 \
  ! videoconvert \
  ! autovideosink
```

Therefore:

```text
[PASS] Device Tree / sensor driver
[PASS] OV13855 detection
[PASS] MIPI CSI / DPHY
[PASS] RKCIF
[PASS] RKISP
[PASS] V4L2 node
[PASS] 1080p NV12 capture
[PASS] ~30 FPS
[PASS] Live preview
```

### Camera warning currently observed

Kernel log may show:

```text
Warning: vblank need >= 1000us if isp work in online, cur 808 us
```

This has **not blocked the current 1080p/30 capture test**. Keep it recorded in case later long-duration or high-load tests expose instability.

---

## 5. Network Baseline

### Current physical network path

At the moment, the Orange Pi gets Internet through the owner's Windows laptop:

```text
Internet / Wi-Fi
      ↓
Windows laptop
      ↓ Internet Connection Sharing (ICS)
Ethernet
      ↓
Orange Pi 5
```

Current Orange Pi local Ethernet address:

```text
192.168.137.49
```

The owner can SSH locally with:

```bash
ssh orangepi@192.168.137.49
```

### Important limitation

With the current topology, the Windows laptop must remain:

- powered on;
- connected to Wi-Fi;
- sharing Internet to Ethernet.

If the laptop is turned off, sleeps, or loses Wi-Fi, the Orange Pi loses Internet/Tailscale connectivity.

### Future improvement

To make the board independent:

1. connect Orange Pi Ethernet directly to a router, **or**
2. add a supported USB/M.2 Wi-Fi adapter.

The original Orange Pi 5 used here has **no onboard Wi-Fi**.

---

## 6. Tailscale Remote Access

Tailscale is installed and working.

```text
Tailscale version: 1.102.4
Orange Pi node:    orangepi5
Tailscale IPv4:    100.67.251.37
```

Remote users should SSH using:

```bash
ssh <linux_user>@100.67.251.37
```

Examples:

```bash
ssh minhnhat@100.67.251.37
ssh nhat_an@100.67.251.37
```

The owner may use either:

```bash
ssh orangepi@192.168.137.49
```

for direct local Ethernet, or:

```bash
ssh orangepi@100.67.251.37
```

through Tailscale.

### Security note

Do **not** share Tailscale auth keys in screenshots/chat.

Any temporary auth key used to register the board should be revoked after use if it is still active.

---

## 7. Linux User / Team Access

Current intended team structure:

```text
/home/orangepi
/home/minhnhat
/home/nhat_an
```

These are **different home directories on the same filesystem**, not different disk partitions.

### `orangepi`

Owner/main board account.

### `minhnhat`

Confirmed created and login tested.

Configured groups include:

```text
sudo
video
render
input
```

Therefore `minhnhat` can:

- use `sudo`;
- access camera/video devices;
- work with rendering/device nodes;
- install packages;
- edit system configuration;
- reboot the board.

### `nhat_an`

Tailscale invitation has been prepared/sent.

Linux account creation and final group membership should be verified on the board with:

```bash
id nhat_an
groups nhat_an
```

If full project permissions are required:

```bash
sudo usermod -aG sudo,video,render,input nhat_an
```

Then logout/login again.

---

## 8. Multi-user Development

Multiple users can SSH into the board at the same time.

Example:

```text
orangepi@orangepi5  -> owner session
minhnhat@orangepi5 -> teammate session
nhat_an@orangepi5  -> teammate session
```

Each SSH session is independent.

However, resources are shared:

```text
CPU
RAM
NPU
camera
storage
network
system services
```

### Important collaboration rules

Avoid:

- editing the exact same file simultaneously;
- running two processes that both require exclusive access to `/dev/video11`;
- rebooting the board without notifying the others;
- running heavy NPU benchmarks while another person is measuring performance;
- changing kernel/Device Tree/system packages without telling the team.

Recommended source layout:

```text
/home/orangepi/<project>
/home/minhnhat/<project>
/home/nhat_an/<project>
```

Use Git with separate branches/clones instead of all users editing one working tree.

Example:

```text
orangepi  -> branch hung
minhnhat  -> branch minhnhat
nhat_an   -> branch nhatan
```

---

## 9. Remote Camera Usage

HDMI is **not required** to use the real OV13855 camera.

A remote teammate can still:

- open `/dev/video11`;
- capture frames;
- run inference using real camera input;
- save output images/video;
- copy results back using `scp`;
- stream video over the network/Tailscale if needed later.

What a remote teammate cannot do is physically:

- move the camera;
- reconnect the MIPI cable;
- change lens/angle;
- alter lighting;
- power-cycle/reseat hardware manually.

---

## 10. Current Project Status

```text
[PASS] Orange Pi 5 hardware boot
[PASS] Ubuntu 22.04 Jammy
[PASS] RK3588S / ARM64
[PASS] 4 GB RAM
[PASS] microSD root filesystem
[PASS] Ethernet Internet via laptop ICS
[PASS] SSH
[PASS] Tailscale remote access
[PASS] Multi-user Linux setup started
[PASS] OV13855 detected
[PASS] Camera3 / MIPI CSI
[PASS] RKCIF
[PASS] RKISP
[PASS] /dev/video11
[PASS] 1920x1080 NV12
[PASS] ~30 FPS capture
[PASS] GStreamer live preview

[NEXT] Verify NPU driver/runtime
[NEXT] Install/check RKNN Runtime
[NEXT] Run a known RKNN sample model
[NEXT] Benchmark NPU latency/FPS
[NEXT] Deploy project PPE model
[NEXT] Integrate camera -> preprocessing -> RKNN -> postprocessing
[NEXT] Add Person–PPE Association
[NEXT] Measure end-to-end FPS/latency/RAM/NPU usage
```

---

## 11. Next Technical Phase: RKNN / NPU

Recommended order:

```text
1. Check Rockchip NPU driver
      ↓
2. Check RKNN Runtime/Lite2
      ↓
3. Run official/known-good RKNN sample
      ↓
4. Verify inference executes on NPU
      ↓
5. Record latency / FPS / memory
      ↓
6. Convert/deploy PPE model to .rknn
      ↓
7. Test image/video input
      ↓
8. Integrate /dev/video11 real-time camera input
      ↓
9. Person–PPE Association
      ↓
10. Full application benchmark
```

The Orange Pi is the **deployment/runtime target**. Model training and most RKNN conversion work should normally be done on the Ubuntu x86_64 development PC, then the `.rknn` artifact is transferred to the Orange Pi.

---

## 12. Useful Commands

### Board information

```bash
cat /etc/os-release
uname -a
lscpu
free -h
lsblk
df -h /
```

### Network

```bash
ip a
ip route
ping -c 4 google.com
```

### Tailscale

```bash
tailscale status
tailscale ip -4
```

### Camera nodes

```bash
v4l2-ctl --list-devices
ls -l /dev/media* /dev/video* 2>/dev/null
```

### Camera media graph

```bash
media-ctl -p -d /dev/media0
media-ctl -p -d /dev/media1
```

### Camera format

```bash
v4l2-ctl -d /dev/video11 --all
v4l2-ctl -d /dev/video11 --list-formats-ext
```

### Set tested 1080p NV12 profile

```bash
v4l2-ctl -d /dev/video11 \
  --set-fmt-video=width=1920,height=1080,pixelformat=NV12
```

### Quick camera streaming test

```bash
v4l2-ctl -d /dev/video11 \
  --stream-mmap=3 \
  --stream-count=300 \
  --stream-to=/dev/null
```

### Live preview when a graphical display is available

```bash
gst-launch-1.0 \
  v4l2src device=/dev/video11 \
  ! video/x-raw,format=NV12,width=1920,height=1080 \
  ! videoconvert \
  ! autovideosink
```

---

## 13. Summary for New Team Members

If you are joining the project now, assume the following baseline is already working:

```text
Orange Pi 5 + Ubuntu
        ↓
OV13855 Camera3
        ↓
MIPI CSI
        ↓
RKCIF
        ↓
RKISP
        ↓
/dev/video11
        ↓
1920x1080 NV12 @ ~30 FPS
```

Remote access is through:

```text
Tailscale IP: 100.67.251.37
```

The next task is **not camera bring-up**.

The next task is:

```text
RK3588S NPU
-> RKNN Runtime
-> sample inference
-> PPE model deployment
-> camera + AI integration
-> benchmarking
```
