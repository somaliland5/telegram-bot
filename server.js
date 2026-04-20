import express from "express";
import cors from "cors";
import { exec } from "child_process";

const app = express();
app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("API is running...");
});

/*
  🔥 TikTok / Video downloader endpoint
*/
app.get("/download", (req, res) => {
  const url = req.query.url;

  if (!url) {
    return res.json({ error: "No URL provided" });
  }

  // yt-dlp command (Railway supports it if installed)
  const cmd = `yt-dlp -f mp4 -g "${url}"`;

  exec(cmd, (err, stdout, stderr) => {
    if (err) {
      return res.json({ error: "Failed to fetch video" });
    }

    const videoUrl = stdout.trim();

    if (!videoUrl) {
      return res.json({ error: "No video found" });
    }

    res.json({
      success: true,
      video: videoUrl
    });
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});
