export const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

export const validatePassword = (password, minLength = 8) => {
  const errors = [];
  
  if (!password) {
    errors.push('Password is required');
    return { isValid: false, errors };
  }
  
  if (password.length < minLength) {
    errors.push(`Password must be at least ${minLength} characters long`);
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }
  
  if (!/\d/.test(password)) {
    errors.push('Password must contain at least one number');
  }
  
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validateUsername = (username) => {
  const errors = [];
  
  if (!username) {
    errors.push('Username is required');
    return { isValid: false, errors };
  }
  
  if (username.length < 3) {
    errors.push('Username must be at least 3 characters long');
  }
  
  if (username.length > 32) {
    errors.push('Username must be no more than 32 characters long');
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    errors.push('Username can only contain letters, numbers, underscores, and hyphens');
  }
  
  if (/^[0-9]/.test(username)) {
    errors.push('Username cannot start with a number');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validateIPAddress = (ip) => {
  const ipv4Regex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
  const ipv6Regex = /^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;
  
  return ipv4Regex.test(ip) || ipv6Regex.test(ip);
};

export const validateSubnetMask = (mask) => {
  const cidrRegex = /^\/([0-9]|[1-2][0-9]|3[0-2])$/;
  const maskRegex = /^(?:(?:255\.){3}(?:255|254|252|248|240|224|192|128|0))|(?:(?:255\.){2}(?:255|254|252|248|240|224|192|128|0)\.0)|(?:(?:255\.){1}(?:255|254|252|248|240|224|192|128|0)\.0\.0)|(?:(?:255|254|252|248|240|224|192|128|0)\.0\.0\.0)$/;
  
  return cidrRegex.test(mask) || maskRegex.test(mask);
};

export const validatePort = (port) => {
  const portNum = parseInt(port, 10);
  return !isNaN(portNum) && portNum >= 1 && portNum <= 65535;
};

export const validateHostname = (hostname) => {
  const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/;
  return hostnameRegex.test(hostname) && hostname.length <= 253;
};

export const validateMacAddress = (mac) => {
  const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
  return macRegex.test(mac);
};

export const validatePath = (path) => {
  if (!path) return false;
  
  const unixPathRegex = /^\/[^<>:"|?*]*$/;
  const windowsPathRegex = /^[a-zA-Z]:\\[^<>:"|?*]*$/;
  
  return unixPathRegex.test(path) || windowsPathRegex.test(path);
};

export const validateShareName = (name) => {
  const errors = [];
  
  if (!name) {
    errors.push('Share name is required');
    return { isValid: false, errors };
  }
  
  if (name.length < 1 || name.length > 80) {
    errors.push('Share name must be between 1 and 80 characters');
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
    errors.push('Share name can only contain letters, numbers, underscores, and hyphens');
  }
  
  const reservedNames = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'];
  if (reservedNames.includes(name.toUpperCase())) {
    errors.push('Share name cannot use reserved system names');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validatePoolName = (name) => {
  const errors = [];
  
  if (!name) {
    errors.push('Pool name is required');
    return { isValid: false, errors };
  }
  
  if (name.length < 1 || name.length > 64) {
    errors.push('Pool name must be between 1 and 64 characters');
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
    errors.push('Pool name can only contain letters, numbers, underscores, and hyphens');
  }
  
  if (/^[0-9]/.test(name)) {
    errors.push('Pool name cannot start with a number');
  }
  
  const reservedNames = ['log', 'mirror', 'raidz', 'raidz1', 'raidz2', 'raidz3', 'spare', 'cache'];
  if (reservedNames.includes(name.toLowerCase())) {
    errors.push('Pool name cannot use reserved ZFS keywords');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const validateRequired = (value, fieldName) => {
  if (!value || (typeof value === 'string' && value.trim() === '')) {
    return {
      isValid: false,
      errors: [`${fieldName} is required`],
    };
  }
  
  return {
    isValid: true,
    errors: [],
  };
};

export const validateRange = (value, min, max, fieldName) => {
  const numValue = parseFloat(value);
  
  if (isNaN(numValue)) {
    return {
      isValid: false,
      errors: [`${fieldName} must be a number`],
    };
  }
  
  if (numValue < min || numValue > max) {
    return {
      isValid: false,
      errors: [`${fieldName} must be between ${min} and ${max}`],
    };
  }
  
  return {
    isValid: true,
    errors: [],
  };
};