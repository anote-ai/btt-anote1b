import { faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import React from "react";

function Banner({ open }) {
  return (
    <div
      className={` ${
        open ? "hidden" : ""
      } flex items-center font-medium justify-around bg-gray-800`}
    >
      <div className="flex items-center justify-around bg-gray-800 py-2.5 px-6 cursor:pointer">
        {/* <a
          onClick={() => {
            // window.open("https://form.jotform.com/233498501418055", "_blank");
            window.location.href = window.location.origin + "/panacea";
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          View Presentations on Generative AI from Anote's Launch of Panacea!
        </a>
        <a
          className="text-[#defe47] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            // window.open(window.location["origin"] + "/panacea");
            window.location.href = window.location.origin + "/panacea";
          }}
        >
          Watch Now
          <FontAwesomeIcon
            className="ml-3 text-[#defe47]"
            icon={faArrowRight}
          />
        </a> */}
                {/* <a
          onClick={() => {
            // window.open("https://form.jotform.com/233498501418055", "_blank");
            window.location.href = window.location.origin + "/events";
            // window.location.assign("https://anote.ai/events");
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          Join Thousands of Enterprise AI Leaders at our Monthly AI Meetups
        </a>
        <a
          className="text-[#defe47] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            // window.open(window.location["origin"] + "/panacea");

            window.location.href = window.location.origin + "/events";
          }}
        >
          Register Here
          <FontAwesomeIcon
            className="ml-3 text-[#defe47]"
            icon={faArrowRight}
          />
        </a> */}
                        {/* <a
          onClick={() => {
            // window.open("https://form.jotform.com/233498501418055", "_blank");
            window.location.href = window.location.origin + "/aidaysummit2025";
            // window.location.assign("https://anote.ai/events");
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          Join Thousands of Enterprise AI Leaders at our AI Day Summit 2025
        </a> */}

        {/* <a
          className="text-[#defe47] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            // window.open(window.location["origin"] + "/panacea");

            window.location.href = window.location.origin + "/aidaysummit2025";
          }}
        >
          Register Here
          <FontAwesomeIcon
            className="ml-3 text-[#defe47]"
            icon={faArrowRight}
          />
        </a> */}
        {/* <a
          onClick={() => {
            // window.open("https://form.jotform.com/233498501418055", "_blank");
            window.location.href = window.location.origin + "/aidaysummit2025";
            // window.location.assign("https://anote.ai/events");
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          Listen to Talks by Enterprise AI Leaders from Anote's AI Day Summit 2025
        </a>
        <a
          className="text-[#defe47] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            // window.open(window.location["origin"] + "/panacea");
            window.location.href = window.location.origin + "/aidaysummit2025";
          }}
        >
          Watch Now!
          <FontAwesomeIcon
            className="ml-3 text-[#defe47]"
            icon={faArrowRight}
          />
        </a> */}
        <a
          onClick={() => {
            window.open("https://anote.ai/palebluedot", "_blank");
          }}
          className="text-white text-xs md:text-sm lg:text-base lg:font-medium m-0"
          style={{ cursor: "pointer" }}
        >
          Join Thousands of AI Leaders for our Gen AI Research and Development Launch
        </a>
        <a
          className="text-[#defe47] text-xs md:text-sm lg:text-base ml-4 hover:underline cursor-pointer"
          onClick={() => {
            window.open(window.location["origin"] + "/palebluedot", "_blank");
          }}
        >
          Register Here
          <FontAwesomeIcon
            className="ml-3 text-[#defe47]"
            icon={faArrowRight}
          />
        </a>
      </div>
    </div>
  );
}

export default Banner;
