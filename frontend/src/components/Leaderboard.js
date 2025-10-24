import React, { useState, useEffect } from "react";

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL ;


const Leaderboard = () => {
  const [openIndex, setOpenIndex] = useState(null);
  const [showTestForm, setShowTestForm] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [fetchError, setFetchError] = useState(null);

  useEffect(() => {
    fetchLeaderboardData();
  }, []);

  const fetchLeaderboardData = async () => {
    try {
      setLoading(true);
      setFetchError(null);
      const response = await fetch(`${API_BASE_URL}/get_datasets`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.status === "success") {
        setDatasets(data.datasets);
      } else {
        throw new Error(data.message || "Failed to fetch datasets");
      }
    } catch (error) {
      console.error("Error fetching leaderboard:", error);
      setFetchError(error.message);
      setDatasets([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClick = (index) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const addDataset = async (datasetData) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/add_dataset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(datasetData),
      });
      const result = await response.json();
      setApiResponse(result);
      
      if (result.status === "success") {
        await fetchLeaderboardData();
      }
      
      return result;
    } catch (error) {
      const errorResult = { status: "error", message: error.message };
      setApiResponse(errorResult);
      return errorResult;
    } finally {
      setLoading(false);
    }
  };

  const addModel = async (modelData) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/add_model`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(modelData),
      });
      const result = await response.json();
      setApiResponse(result);
      
      if (result.status === "success") {
        await fetchLeaderboardData();
      }
      
      return result;
    } catch (error) {
      const errorResult = { status: "error", message: error.message };
      setApiResponse(errorResult);
      return errorResult;
    } finally {
      setLoading(false);
    }
  };

  const testAddDataset = () => {
    const testData = {
      name: "Test Dataset - Classification " + Date.now(),
      url: "https://example.com/test-dataset",
      task_type: "text_classification",
      description: "A test dataset for classification tasks",
      models: [
        {
          rank: 1,
          model: "Test Model 1",
          score: 0.95,
          ci: "0.93 - 0.97",
          updated: "Dec 2024"
        }
      ]
    };
    addDataset(testData);
  };

  const testAddModel = () => {
    const firstDataset = datasets.length > 0 ? datasets[0].name : "FinanceBench - Retrieval Accuracy";
    
    const testData = {
      dataset_name: firstDataset,
      model: "Test Model " + Date.now(),
      score: Math.random() * 0.3 + 0.65,
      ci: "0.90 - 0.94",
      updated: "Dec 2024"
    };
    addModel(testData);
  };

  const faqs = [
    {
      question: "Where can I find the evaluation datasets",
      answer: "You can access the evaluation set by following the dataset link listed with our submit to leaderboard component. If you have difficulty downloading them or need direct access, just send us an email at nvidra@anote.ai and we will provide the questions promptly.",
    },
    {
      question: "How many times can I submit?",
      answer: "There's no strict limit on submissions. You're welcome to submit multiple times, but for the most meaningful insights, we encourage you to submit only when there are substantial updates or improvements to your model.",
    },
    {
      question: "What am I expected to submit?",
      answer: "We only require the outputs your model generates for each query in the evaluation set. You do not need to share model weights, code, or other confidential information—simply the answers.",
    },
    {
      question: "When can I expect to receive the results for my submission?",
      answer: "We typically process and evaluate new submissions within a few business days. Once your results are ready, we will contact you via email with your score and ranking details.",
    },
    {
      question: "Do I need to give my LLM extra information to accurately run the tests?",
      answer: "We do not mandate any special pre-training or additional data, though you could use our fine tuning API. The goal is to see how your model performs under realistic conditions.",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 pb-20 mx-3">
      <h1 className="text-4xl font-bold text-white mb-4 mt-8">LLM Leaderboards</h1>
      
      <div className="bg-gray-800 p-6 rounded-lg mb-8 w-full max-w-4xl">
        <h2 className="text-2xl font-bold text-white mb-4">API Test Panel</h2>
        
        <div className="flex gap-4 mb-4 flex-wrap">
          <button
            onClick={testAddDataset}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-md font-semibold transition-colors"
          >
            {loading ? "Loading..." : "Test Add Dataset"}
          </button>
          
          <button
            onClick={testAddModel}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-md font-semibold transition-colors"
          >
            {loading ? "Loading..." : "Test Add Model"}
          </button>
          
          <button
            onClick={fetchLeaderboardData}
            disabled={loading}
            className="bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 text-white px-4 py-2 rounded-md font-semibold transition-colors"
          >
            {loading ? "Loading..." : "Refresh Data"}
          </button>
          
          <button
            onClick={() => setShowTestForm(!showTestForm)}
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md font-semibold transition-colors"
          >
            {showTestForm ? "Hide" : "Show"} Custom Form
          </button>
        </div>

        {fetchError && (
          <div className="bg-red-900 border border-red-700 p-4 rounded-md mb-4">
            <h3 className="text-lg font-semibold text-red-200 mb-2">Error Loading Data:</h3>
            <p className="text-red-300 text-sm">{fetchError}</p>
          </div>
        )}

        {apiResponse && (
          <div className="bg-gray-700 p-4 rounded-md mb-4">
            <h3 className="text-lg font-semibold text-white mb-2">API Response:</h3>
            <pre className={`${apiResponse.status === "success" ? "text-green-400" : "text-red-400"} text-sm overflow-auto`}>
              {JSON.stringify(apiResponse, null, 2)}
            </pre>
          </div>
        )}

        {showTestForm && (
          <div className="bg-gray-700 p-4 rounded-md">
            <h3 className="text-lg font-semibold text-white mb-4">Custom Test Form</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="text-white font-medium mb-2">Add Dataset:</h4>
                <button
                  onClick={() => {
                    const customData = {
                      name: "Custom Dataset - " + Date.now(),
                      url: "https://example.com/custom",
                      task_type: "text_classification",
                      description: "Custom test dataset"
                    };
                    addDataset(customData);
                  }}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm"
                >
                  Add Custom Dataset
                </button>
              </div>
              <div>
                <h4 className="text-white font-medium mb-2">Add Model:</h4>
                <button
                  onClick={() => {
                    const firstDataset = datasets.length > 0 ? datasets[0].name : "Test Dataset";
                    const customData = {
                      dataset_name: firstDataset,
                      model: "Custom Model - " + Date.now(),
                      score: Math.random() * 0.5 + 0.5,
                      updated: new Date().toISOString().split("T")[0]
                    };
                    addModel(customData);
                  }}
                  className="bg-green-500 hover:bg-green-600 text-white px-3 py-1 rounded text-sm"
                >
                  Add Custom Model
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <button
        className="bg-black hover:bg-gray-800 text-white px-6 py-2 mb-8 rounded-md text-lg font-semibold transition-colors"
        onClick={() => window.open("https://docs.google.com/forms/d/e/1FAIpQLSdydF_8sfJQP0ub6VLs9uced32kfHxrvlQzyFRf0IhR1MlMRg/viewform?usp=dialog", "_blank")}
      >
        Submit Model to Leaderboard
      </button>

      {loading && datasets.length === 0 && (
        <div className="text-white text-xl mb-8">Loading leaderboard data...</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-7xl px-4">
        {datasets.map((dataset, index) => {
          return (
            <div
              key={dataset.id || index}
              className="w-full p-4 bg-gray-950 rounded-lg shadow-lg"
            >
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-white">{dataset.name}</h2>
                <a
                  href={dataset.url}
                  className="text-blue-400 hover:text-blue-500 text-sm underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View Dataset
                </a>
              </div>
              <div className="grid grid-cols-4 text-white font-bold text-center bg-gray-900 p-4 rounded-t-lg">
                <div>Rank</div>
                <div>Model</div>
                <div>Score</div>
                <div>Updated</div>
              </div>
              <div>
                {dataset.models && dataset.models.length > 0 ? (
                  dataset.models.map((model, modelIndex) => {
                    return (
                      <div
                        key={modelIndex}
                        className={`grid grid-cols-4 text-center p-4 ${
                          modelIndex % 2 === 0
                            ? "bg-gray-700 text-white"
                            : "bg-gray-800 text-white"
                        }`}
                      >
                        <div>{model.rank}</div>
                        <div>{model.model}</div>
                        <div>{model.score}</div>
                        <div>{model.updated}</div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center p-4 text-gray-400">No models yet</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!loading && datasets.length === 0 && (
        <div className="text-white text-center mt-8">
          <p className="text-xl mb-2">No datasets found</p>
          <p className="text-gray-400">Use the API test panel above to add datasets</p>
        </div>
      )}

      <div className="w-full md:w-3/4 mx-auto mt-20">
        <div className="bg-gray-900 rounded-xl p-10">
          <div className="text-yellow-500 text-3xl font-semibold mb-8">FAQs</div>
          {faqs.map((faq, index) => {
            return (
              <div
                className="bg-gray-800 px-5 py-4 my-4 rounded-xl cursor-pointer"
                onClick={() => handleClick(index)}
                key={index}
              >
                <div className="faq-header">
                  <h2 className="text-xl font-medium text-blue-400">
                    {faq.question}
                  </h2>
                </div>
                {openIndex === index && (
                  <div className="faq-answer mt-2 text-white">
                    <p>{faq.answer}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Leaderboard;