import LandingPage from "./landing_page/LandingPage";
import ReactGA4 from "react-ga4";
import { BrowserRouter as Router, useLocation } from "react-router-dom";
import { useEffect } from "react";
ReactGA4.initialize("G-CMN1GX5JE1");

function PageTracker({subdomain}) {
  let location = useLocation();

  useEffect(() => {
    ReactGA4.send({
      hitType: 'pageview',
      page: subdomain + "/" + location.pathname,
    });
  }, [location]);

  return null; // This component does not render anything
}

function App() {
  return (
    <Router>
      <PageTracker subdomain="landingpage" />
      <LandingPage />
    </Router>
  );
}

export default App;
