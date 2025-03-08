const fs = require('fs');
const { marked } = require('marked');
const express = require('express');
const archiver = require('archiver');
const path = require('path');
const matter = require('gray-matter');
const sqlite3 = require('sqlite3');
const multer = require('multer');
const admZip = require('adm-zip');


// dotenv config
require('dotenv').config();

// sqlite3 config
const db = new sqlite3.Database("rec.db", (e) => {
  if (e) throw e;
});

// express config
const app = express();
const PORT = 2020;

// multer config
const upload = multer({ dest: 'uploads/' });

// Serve static files from the 'public' directory
app.set('trust proxy', true)
app.use(express.static(path.join(__dirname, 'public')));
app.use('/docs', express.static(path.join(__dirname, 'docs')));
app.use(express.json());

// root serving
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.get('/entry/:d', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'entry.html'));
});

app.get('/req-visions', (req, res) => {
  const entryPath = path.join(__dirname, 'docs/ex/visions.md');
  fs.readFile(entryPath, 'utf8', (err, data) => {
    if (err) {
      return res.status(404).json({ error: 'The dev sames to lack vision (wtf?'})
    }
    const { data: frontmatter, content } = matter(data);

    const title = `Visions for ${frontmatter.period || 'Future'}`
    const dateline = frontmatter.period || 'NULL';
    const htmlContent = marked(content);
    const body = {
      title,
      dateline,
      content: htmlContent,
      ...frontmatter
    };
    res.json(body);
  });
})

app.get('/req-entry', (req, res) => {
  const { d } = req.query;
  if (!d) {
    return res.status(400).json({ error: "Missing data query parameter." });
  }
  
  const entryPath = path.join(__dirname, 'docs', `${d}/entry.md`);

  fs.readFile(entryPath, 'utf8', (err, data) => {
    if (err) {
      console.error('Error reading file:', err);
      return res.status(404).json({ error: 'Entry not found.' });
    }
    try {
      const { data: frontmatter, content } = matter(data);
      const title = frontmatter.title || `Diary @ ${d}`;
      const dateline = d;
  
      if (frontmatter.locked) {
        const api_key = req.get('x-api-key');
        if (api_key != process.env.DIARY_VIEW_KEY) {
          return res.status(403).json({ error: 'Forbidden: Invalid API Key.' });
        }
      }
  
      const htmlContent = marked(content);
      const body = {
        data,
        title,
        dateline,
        content: htmlContent,
        ...frontmatter
      };
      console.log(body);
      res.json(body);
    } catch (err) {
      console.error('Error processing markdown:', err);
      return res.status(500).json({ error: 'Error processing markdown content.' });
    }
  });  
});

app.get('/download-assets', (req, res) => {
  const { d } = req.query;

  if (!d) {
    return res.status(400).json({ error: 'Missing data query parameter.' });
  }

  const assetsDir = path.join(__dirname, 'docs', `${d}/assets`);
  const zipFilePath = path.join(__dirname, 'docs', `${d}/assets.zip`);

  // Check if the assets directory exists
  fs.exists(assetsDir, (exists) => {
    if (!exists) {
      return res.status(404).json({ error: 'Assets directory not found.' });
    }

    // Create a zip file (overwrite if it already exists)
    const output = fs.createWriteStream(zipFilePath);
    const archive = archiver('zip', {
      zlib: { level: 9 } // Maximum compression
    });

    // Pipe the archive to the output zip file
    archive.pipe(output);

    // Append files from the assets directory to the archive
    archive.directory(assetsDir, false);

    archive.finalize();

    // When the zip file is created, stream it to the response
    output.on('close', () => {
      // Set the proper headers for file download
      res.setHeader('Content-Disposition', `attachment; filename=${path.basename(zipFilePath)}`);
      res.setHeader('Content-Type', 'application/zip');

      // Stream the zip file to the response
      const fileStream = fs.createReadStream(zipFilePath);
      fileStream.pipe(res);

      fileStream.on('error', (err) => {
        console.error('Error reading the zip file:', err);
        res.status(500).json({ error: 'Error reading asset ZIP file.' });
      });
    });

    // Handle any errors during zipping
    archive.on('error', (err) => {
      console.error('Error creating zip archive:', err);
      res.status(500).json({ error: 'Error creating zip archive.' });
    });
  });
});

app.get('/latest-entries', (req, res) => {
  const { limit = 10 } = req.query;
  const numericLimit = parseInt(limit, 10);

  if (isNaN(numericLimit) || numericLimit <= 0) {
    return res.status(400).json({ error: 'Invalid limit parameter' });
  }
  db.all('SELECT * FROM docs ORDER BY id DESC LIMIT ?', [numericLimit], (err, rows) => {
    if (err) {
      return res.status(500).json({ error: 'Error fetching entries from database' });
    }
    res.json(rows);
  });
})

app.post('/post-entry', (req, res) => {
  const api_key = req.get('x-api-key');
  if (api_key != process.env.DIARY_SUBMIT_KEY) {
    return res.status(403).json({ error: 'Forbidden: Invalid API Key.'});
  }

  const { filename, contents } = req.body;
  const entryPath = path.join(__dirname, 'docs', `${filename}/entry.md`);
  
  // Check if the file already exists (using fs.stat to check the file directly)
  fs.stat(entryPath, (err, stats) => {
    if (!err && stats.isFile()) {
      return res.status(403).json({ error: 'File already exists, cannot overwrite.' });
    }

    // Create the directory if it doesn't exist
    fs.mkdir(path.join(__dirname, 'docs', filename), { recursive: true }, (mkdirErr) => {
      if (mkdirErr) {
        console.error('Error creating directory:', mkdirErr);
        return res.status(500).json({ error: 'Error creating directory.' });
      }

      // Append the contents to the file
      fs.appendFile(entryPath, contents, 'utf8', (writeErr) => {
        if (writeErr) {
          console.error('Error writing to file:', writeErr);
          return res.status(500).json({ error: 'Error writing to file.' });
        }

        // Insert into the database
        db.run('INSERT INTO docs (filename) values (?)', [filename], (dbErr) => {
          if (dbErr) {
            console.error('Error writing to database:', dbErr);
            return res.status(500).json({ error: 'Error writing to file index system.' });
          }
          res.status(201).json({ message: 'File created successfully!' });
        });
      });
    });
  });
});

app.post('/upload-assets/:filename', upload.single('zipfile'), (req, res) => {
  console.log('called')
  const { filename } = req.params;
  const entryDir = path.join(__dirname, 'docs', filename); // Entry directory for this filename
  const assetsDir = path.join(entryDir, 'assets'); // Assets directory for the entry

  const api_key = req.get('x-api-key');
  console.log('called 2')

  if (api_key != process.env.DIARY_SUBMIT_KEY) {
    return res.status(403).json({ error: 'Forbidden: Invalid API Key.'});
  }
  console.log('called 3')
  if (!fs.existsSync(entryDir)) {
    return res.status(404).json({ error: `Entry directory for ${filename} not found.` });
  }
  console.log('called 4')
  if (!fs.existsSync(assetsDir)) {
    fs.mkdirSync(assetsDir, { recursive: true });
  }
  console.log('called 5');
  console.log(req.file.mimetype);
  if (req.file && req.file.mimetype === 'application/zip') {
    console.log('called 6')
    try {
      const zip = new admZip(req.file.path);
      zip.extractAllTo(assetsDir, true);
      fs.unlinkSync(req.file.path);
      res.status(200).json({ message: `Assets successfully uploaded to ${req.file.path}`});
    } catch (err) {
      res.status(500).json({ error: `Error extracting zip file: ${err.message}` });
    }
  }
  console.log('called ???')
})

app.post('/update-entry', (req, res) => {
  const api_key = req.get('x-api-key');
  if (api_key != process.env.DIARY_SUBMIT_KEY) {
    return res.status(403).json({ error: 'Forbidden: Invalid API Key.'});
  }
  const { filename, contents } = req.body;
  fs.exists(path.join(__dirname, 'docs', `${filename}/entry.md`), (exists) => {
    if (!exists) {
      return res.status(403).json({ error: 'File doesn\'t exists, cannot overwrite.' });
    }

    fs.writeFile(path.join(__dirname, 'docs', `${filename}/entry.md`), contents, 'utf8', (err) => {
      if (err) {
        console.log(err);
        return res.status(500).json({ error: 'Error writing to file.' });
      }
      res.status(201).json({ message: 'File updated successfully!' });
    })
  })
})

app.listen(PORT, () => {
    console.log(`Server listening on port: ${PORT}`);
});