/**
 * Webpack Optimization Configuration
 * Additional optimizations for production builds
 */

module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
          reuseExistingChunk: true,
        },
        common: {
          minChunks: 2,
          priority: 5,
          reuseExistingChunk: true,
        },
        // Separate large libraries
        react: {
          test: /[\\/]node_modules[\\/](react|react-dom|react-router)[\\/]/,
          name: 'react',
          priority: 20,
        },
        tanstack: {
          test: /[\\/]node_modules[\\/]@tanstack[\\/]/,
          name: 'tanstack',
          priority: 15,
        },
        ui: {
          test: /[\\/]node_modules[\\/](@headlessui|@heroicons|framer-motion)[\\/]/,
          name: 'ui',
          priority: 15,
        },
      },
    },
    runtimeChunk: 'single',
    moduleIds: 'deterministic',
    minimize: true,
    usedExports: true,
    sideEffects: false,
  },
  performance: {
    hints: 'warning',
    maxEntrypointSize: 512000, // 500kb
    maxAssetSize: 512000, // 500kb
  },
};
