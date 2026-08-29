module.exports = {
  preset: '@react-native/jest-preset',
  transformIgnorePatterns: [
    'node_modules/(?!((@)?react-native|react-native-.*|@react-native(-community)?|@react-navigation|@react-native-async-storage)/)',
  ],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
