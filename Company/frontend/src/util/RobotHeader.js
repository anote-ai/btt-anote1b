
export function robotHeader() {
    const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT;
    var robotsHeader = [];
    if (API_ENDPOINT == "https://api.tryanote-staging.com") {
        robotsHeader = <meta name="robots" content="noindex, nofollow" />;
    }
    return robotsHeader;
}