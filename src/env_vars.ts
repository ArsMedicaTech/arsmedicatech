//const API_URL = 'https://demo.arsmedicatech.com';
//const API_URL = process.env.API_URL || 'http://localhost:3123';

const API_URL = process.env.API_URL || process.env.REACT_APP_API_URL || null;
if (!API_URL) {
  throw new Error('API_URL environment variable is not set');
}

console.log('API_URL:', API_URL);

const SENTRY_DSN =
  process.env.SENTRY_DSN || process.env.REACT_APP_SENTRY_DSN || null;
console.log('SENTRY_DSN:', SENTRY_DSN, process.env);
if (!SENTRY_DSN) {
  throw new Error('SENTRY_DSN environment variable is not set');
}

console.log('SENTRY_DSN:', SENTRY_DSN);

const LIVE_KIT_TOKEN_URL = 'https://demo.arsmedicatech.com';
const LIVE_KIT_SERVER_URL = 'wss://demo.arsmedicatech.com';

const GOOGLE_LOGO =
  'https://darrenmackenzie-chalice-bucket.s3.us-east-1.amazonaws.com/icons/Google_logo.svg';

const DEBUG = process.env.NODE_ENV === 'development';

export {
  API_URL,
  DEBUG,
  GOOGLE_LOGO,
  LIVE_KIT_SERVER_URL,
  LIVE_KIT_TOKEN_URL,
  SENTRY_DSN,
};
