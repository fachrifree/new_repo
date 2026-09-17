export function env(name, fallback = '') {
  try {
    return Netlify.env.get(name) ?? fallback;
  } catch {
    return process.env[name] ?? fallback;
  }
}

export function boolEnv(name, fallback = false) {
  const value = env(name, String(fallback)).toLowerCase();
  return ['1', 'true', 'yes', 'on'].includes(value);
}

export function numEnv(name, fallback) {
  const value = Number(env(name, String(fallback)));
  return Number.isFinite(value) ? value : fallback;
}

export const defaultQuery = () => env(
  'MONITOR_QUERY',
  '"BP Tapera" OR Tapera OR FLPP OR "rumah subsidi" OR "KPR subsidi"'
);
