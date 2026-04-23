import { faqsPath } from '../constants/RouteConstants';

export function IsDashboardSubdomain() {
    // Get the full hostname from the location object
    const hostname = window.location.hostname;
    const hostnameParts = hostname.split('.');
    // If the hostname has more than two parts, the first part is the subdomain
    if (hostnameParts.length > 1) {
      const subdomain = hostnameParts[0];
      if (subdomain === "dashboard") {
        return true;
      } else {
        return false;
      }
    } else {
      // If there is no subdomain, return false
      return false;
    }
}

export function IsMetricsSubdomain() {
    // Get the full hostname from the location object
    const hostname = window.location.hostname;
    const hostnameParts = hostname.split('.');
    // If the hostname has more than two parts, the first part is the subdomain
    if (hostnameParts.length > 1) {
      const subdomain = hostnameParts[0];
      if (subdomain === "metrics") {
        return true;
      } else {
        return false;
      }
    } else {
      // If there is no subdomain, return false
      return false;
    }
}

export function GetFaqsUrl() {
    // Get the full hostname from the location object
    const hostname = window.location.hostname;
    const hostnameParts = hostname.split('.');
    // If the hostname has more than two parts, the first part is the subdomain
    var realDomain = hostnameParts[0];
    if (hostnameParts.length > 1) {
        realDomain = "";
        for (var i = 1; i < hostnameParts.length; i++) {
          realDomain += hostnameParts[i];
          if (i != hostnameParts.length - 1) {
            realDomain += ".";
          }
        }
    }

    var maybePort = window.location.port;
    if (maybePort.length != 0) {
        maybePort = ":" + maybePort;
    }

    return `${window.location.protocol}//${realDomain}${maybePort}${faqsPath}`;
}


export function GetHomeUrl() {
  // Get the full hostname from the location object
  const hostname = window.location.hostname;
  const hostnameParts = hostname.split('.');
  // If the hostname has more than two parts, the first part is the subdomain
  var realDomain = hostnameParts[0];
  if (hostnameParts.length > 1) {
      realDomain = "";
      for (var i = 1; i < hostnameParts.length; i++) {
        realDomain += hostnameParts[i];
        if (i != hostnameParts.length - 1) {
          realDomain += ".";
        }
      }
  }

  var maybePort = window.location.port;
  if (maybePort.length != 0) {
      maybePort = ":" + maybePort;
  }

  return `${window.location.protocol}//${realDomain}${maybePort}`;
}

// export function GetDashboardUrl() {
//   // Get the full hostname from the location object
//   const hostname = window.location.hostname;
//   const hostnameParts = hostname.split('.');
//   // If the hostname has more than two parts, the first part is the subdomain
//   var realDomain = hostnameParts[0];
//   if (hostnameParts.length > 1) {
//       realDomain = hostnameParts[1];
//   }

//   var maybePort = window.location.port;
//   if (maybePort.length != 0) {
//       maybePort = ":" + maybePort;
//   }

//   return `${window.location.protocol}//dashboard.${realDomain}${maybePort}`;
// }

export function GetDashboardUrl() {
  return `https://dashboard.anote.ai`;
}

export function GetPrivateGPTDashboardUrl() {
  return `https://anote.ai/downloadprivategpt`;
}


export function GetSababaUrl() {
  return `https://anote.ai`;
}