# Sourced by open_stack.sh, open_library.sh and play_xt3d.sh (x1-03, 27 Nov).
# XTALK_GPU=1 draws on the graphics card (his RTX 3060 through WSLg's D3D12) instead of the CPU (llvmpipe).
#   XTALK_GPU=1 ~/projects/xtalk_py/tools/play_xt3d.sh SquadBuggy
# Measured 27 Nov, 900x600, 300 frames: draw time 2-4x shorter in every 3D game; Squad Buggy 46 -> 58 fps,
# Dot Maze 32 -> 33 a second (its cost is the script, not the drawing). Same pictures.
# Not the default until the owner says so.
if [ "${XTALK_GPU:-0}" = 1 ]; then
  export GALLIUM_DRIVER=d3d12
  export MESA_D3D12_DEFAULT_ADAPTER_NAME="${XTALK_GPU_NAME:-NVIDIA}"
fi
