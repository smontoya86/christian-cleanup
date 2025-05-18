// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  // Optional: If you need to mock CSS/Sass/Less imports in your JS files (not common for inline scripts)
  // moduleNameMapper: {
  //   '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  // },
  // Specify where to find test files
  testMatch: [
    '**/tests/javascript/**/*.test.js',
    // If you want Jest to also pick up Python tests (less common, usually pytest handles Python):
    // '**/tests/unit/**/*.test.py', 
    // '**/tests/integration/**/*.test.py',
  ],
  // Optional: Setup files to run before each test file (e.g., for global mocks)
  // setupFilesAfterEnv: ['./tests/javascript/setupTests.js'],

  // Collect coverage from JS files in static, but exclude large libraries if any are vendored in
  collectCoverage: true,
  collectCoverageFrom: [
    'app/static/js/**/*.js', // If JS is extracted to static files
    // We can't directly collect coverage from inline scripts in HTML templates with Jest easily.
    // For now, we'll focus on testing the logic as if it were in a separate file.
  ],
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/tests/'
  ],
  coverageReporters: ['text', 'lcov', 'html'], // Generates an HTML coverage report in 'coverage/' dir
};
