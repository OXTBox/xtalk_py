# Sourced by open_stack.sh, open_library.sh and play_xt3d.sh (x1-03, 27 Nov).
# Draws on the graphics card (his RTX 3060 through WSLg's D3D12) instead of the CPU (llvmpipe).
# Owner 27 Nov: "default". XTALK_GPU=0 in front goes back to the CPU.
# Measured 27 Nov, 900x600, 300 frames: draw time 2-4x shorter in every 3D game; Squad Buggy 46 -> 58 fps,
# Dot Maze 32 -> 33 a second (its cost is the script, not the drawing). Same pictures.
# Other computers: only WSL needs this (Windows itself, a Mac or a Linux with its own driver already use the
# card). So it is set only when this is WSL with a graphics card shared in (/dev/dxg) and Mesa's d3d12 driver
# present; anywhere else nothing changes. The NVIDIA name is a preference: a computer without one gets its
# first card (XTALK_GPU_NAME picks another, e.g. AMD or Intel).
if [ "${XTALK_GPU:-1}" = 1 ] && [ -e /dev/dxg ] && ls /usr/lib/*/dri/d3d12_dri.so >/dev/null 2>&1; then
  export GALLIUM_DRIVER=d3d12
  export MESA_D3D12_DEFAULT_ADAPTER_NAME="${XTALK_GPU_NAME:-NVIDIA}"
fi
