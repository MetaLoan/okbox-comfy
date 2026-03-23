const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 8080;
const UPLOAD_DIR = '/data/videos';
const BASE_URL = process.env.BASE_URL || '';
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';
const MAX_AGE_HOURS = parseInt(process.env.MAX_AGE_HOURS || '72'); // Auto-cleanup after 72h

// Ensure upload directory exists
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: UPLOAD_DIR,
  filename: (req, file, cb) => {
    const hash = crypto.randomBytes(8).toString('hex');
    const ext = path.extname(file.originalname) || '.mp4';
    cb(null, `${hash}${ext}`);
  }
});
const upload = multer({ storage, limits: { fileSize: 500 * 1024 * 1024 } }); // 500MB max

// Auth middleware (optional - if AUTH_TOKEN is set)
function checkAuth(req, res, next) {
  if (!AUTH_TOKEN) return next();
  const token = req.headers['authorization']?.replace('Bearer ', '') || req.query.token;
  if (token !== AUTH_TOKEN) return res.status(401).json({ error: 'Unauthorized' });
  next();
}

// Upload endpoint
app.post('/upload', checkAuth, upload.single('file'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });

  const filename = req.file.filename;
  const url = `${BASE_URL || `https://${req.hostname}`}/v/${filename}`;

  console.log(`Uploaded: ${filename} (${(req.file.size / 1024 / 1024).toFixed(1)}MB)`);

  res.json({
    url,
    filename,
    size: req.file.size,
    created: new Date().toISOString()
  });
});

// Serve video files
app.get('/v/:filename', (req, res) => {
  const filepath = path.join(UPLOAD_DIR, req.params.filename);
  if (!fs.existsSync(filepath)) return res.status(404).json({ error: 'Not found' });

  const stat = fs.statSync(filepath);
  const ext = path.extname(req.params.filename).toLowerCase();
  const mimeTypes = {
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
  };

  res.set({
    'Content-Type': mimeTypes[ext] || 'application/octet-stream',
    'Content-Length': stat.size,
    'Cache-Control': 'public, max-age=86400',
  });

  // Support range requests for video streaming
  const range = req.headers.range;
  if (range) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
    res.status(206).set({
      'Content-Range': `bytes ${start}-${end}/${stat.size}`,
      'Content-Length': end - start + 1,
      'Accept-Ranges': 'bytes',
    });
    fs.createReadStream(filepath, { start, end }).pipe(res);
  } else {
    fs.createReadStream(filepath).pipe(res);
  }
});

// List files (admin)
app.get('/list', checkAuth, (req, res) => {
  const files = fs.readdirSync(UPLOAD_DIR).map(f => {
    const stat = fs.statSync(path.join(UPLOAD_DIR, f));
    return { filename: f, size: stat.size, created: stat.birthtime };
  });
  res.json({ count: files.length, files });
});

// Health check
app.get('/health', (req, res) => res.json({ status: 'ok', videos: fs.readdirSync(UPLOAD_DIR).length }));

// Auto-cleanup old files
setInterval(() => {
  const now = Date.now();
  const maxAge = MAX_AGE_HOURS * 60 * 60 * 1000;
  fs.readdirSync(UPLOAD_DIR).forEach(f => {
    const filepath = path.join(UPLOAD_DIR, f);
    const stat = fs.statSync(filepath);
    if (now - stat.mtimeMs > maxAge) {
      fs.unlinkSync(filepath);
      console.log(`Cleaned up: ${f}`);
    }
  });
}, 60 * 60 * 1000); // Run every hour

app.listen(PORT, () => console.log(`Video storage running on port ${PORT}`));
