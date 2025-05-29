import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";

export async function POST(req: NextRequest) {
  const { repoUrl } = await req.json();

  if (!repoUrl) {
    return NextResponse.json({ error: "Repository URL is required" }, { status: 400 });
  }

  console.log("Generating README for:", repoUrl);

  return new Promise((resolve) => {
    const env = { ...process.env, PYTHONIOENCODING: "utf-8" };
    const python = spawn("python", [
      "d:/Mrudula/B.E/MLSA/GitHubReadme/ai_readme_creator.py",
      repoUrl
    ], { env });

    let output = "";
    let error = "";

    python.stdout.on("data", (data) => {
      console.log("Python output:", data.toString());
      output += data.toString();
    });

    python.stderr.on("data", (data) => {
      console.error("Python error:", data.toString());
      error += data.toString();
    });

    python.on("close", (code) => {
      console.log("Python process exited with code:", code);
      if (code === 0 && output) {
        resolve(NextResponse.json({ readme: output }));
      } else {
        resolve(
          NextResponse.json(
            { error: error || "Failed to generate README" },
            { status: 500 }
          )
        );
      }
    });
  });
}