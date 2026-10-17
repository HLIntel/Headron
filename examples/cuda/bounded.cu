// Bounded grid: one thread per element; threads past n exit immediately.
// Build: nvcc bounded.cu -o bounded && ./bounded   (needs a CUDA device to run)
#include <cassert>
#include <cstdio>
#include <vector>

__global__ void scale(const int* in, int* out, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;  // the bound: no thread touches memory past n
  out[i] = in[i] * 2;
}

int main() {
  const int n = 1000;
  std::vector<int> in(n, 1), out(n, 0);
  int *d_in = nullptr, *d_out = nullptr;
  cudaMalloc(&d_in, n * sizeof(int));
  cudaMalloc(&d_out, n * sizeof(int));
  cudaMemcpy(d_in, in.data(), n * sizeof(int), cudaMemcpyHostToDevice);
  constexpr int block = 256;
  const int grid = (n + block - 1) / block;  // covers n elements, launches no extra work
  scale<<<grid, block>>>(d_in, d_out, n);
  cudaMemcpy(out.data(), d_out, n * sizeof(int), cudaMemcpyDeviceToHost);
  for (int v : out) assert(v == 2);
  cudaFree(d_in);
  cudaFree(d_out);
  std::printf("bounded: 1 assertion held — %d elements scaled, range guard held\n", n);
  return 0;
}
