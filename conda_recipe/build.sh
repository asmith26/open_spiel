git clone -b 'v2.2.4' --single-branch --depth 1 https://github.com/pybind/pybind11.git
git clone -b 'develop' --single-branch --depth 1 https://github.com/jblespiau/dds.git  open_spiel/games/bridge/double_dummy_solver
git clone -b 'master' --single-branch --depth 1 https://github.com/abseil/abseil-cpp.git open_spiel/abseil-cpp

#cd open_spiel
mkdir build
cd build
CXX=g++ cmake -DPython_TARGET_VERSION=3.6 -DCMAKE_CXX_COMPILER=${CXX} ../open_spiel
make -j$(nproc)
#ctest -j$(nproc)
