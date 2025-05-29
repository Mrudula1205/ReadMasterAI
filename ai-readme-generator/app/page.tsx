"use client";
import { useState } from "react";

export default function Home() {
  const [repoUrl, setRepoUrl] = useState("");
  const [readme, setReadme] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    setReadme("");
    
    try {
      const response = await fetch("/api/generate-readme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repoUrl }),
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || "Failed to generate README");
      }

      if (data.readme) {
        setReadme(data.readme);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8">🤖 ReadMaster AI</h1>
      <p className="text-gray-600 mb-8">Generate professional README files for your GitHub repositories</p>

      {/* Input and Generate Button */}
      <div className="w-full max-w-xl mb-8">
        <input
          type="text"
          className="border p-2 w-full mb-4 rounded"
          placeholder="https://github.com/owner/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
        />
        <button
          className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors disabled:bg-blue-300"
          onClick={handleGenerate}
          disabled={loading}
        >
          {loading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              <span>Generating...</span>
            </div>
          ) : (
            "Generate README"
          )}
        </button>
      </div>

      {error && <div className="text-red-600 mb-4">{error}</div>}

      {/* README Code View */}
      {readme && (
        <div className="w-full max-w-4xl mt-6">
          <div className="border rounded-lg overflow-hidden">
            <div className="p-4 bg-gray-50">
              <pre className="text-sm bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto max-h-[600px] whitespace-pre-wrap">
                {readme}
              </pre>
            </div>
          </div>

          {/* Download button */}
          <div className="mt-4 flex justify-end">
            <a
              href={`data:text/markdown;charset=utf-8,${encodeURIComponent(readme)}`}
              download="README.md"
              className="inline-flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm11.78-1.72a.75.75 0 00-1.06-1.06L6.75 9.19 5.28 7.72a.75.75 0 00-1.06 1.06l2 2a.75.75 0 001.06 0l4.5-4.5z" />
              </svg>
              <span>Download README.md</span>
            </a>
          </div>
        </div>
      )}
    </main>
  );
}