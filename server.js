const express = require("express");
const fetch = require("node-fetch");
const app = express();

app.use(express.json());

app.post("/download", async (req, res) => {
  const url = req.body.url;
  if(!url) return res.status(400).json({error:"No URL"});

  try {
    const response = await fetch(`https://tikwm.com/api/?url=${encodeURIComponent(url)}`);
    const data = await response.json();
    res.json({ video: data.data.play });
  } catch (err) {
    res.status(500).json({ error: "Failed to fetch video" });
  }
});

app.get("/", (req,res)=>{
  res.send("Server Running ✅");
});

app.listen(3000, ()=> console.log("Server started"));
