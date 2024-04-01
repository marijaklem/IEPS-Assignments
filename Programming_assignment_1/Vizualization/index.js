const express = require('express');
const bodyParser = require('body-parser');
const { Pool } = require('pg');
const path = require('path');

const app = express();
const port = 3000;

const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'postgres',
  password: '',
  port: 5432,
});

app.use(bodyParser.json());
// Serve static files (HTML, CSS, JavaScript)
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/pages', async (req, res) => {
  try {
    const client = await pool.connect();
    const result = await client.query('SELECT id, url FROM crawldb.page WHERE page_type_code = $1 AND http_status_code = $2', ['HTML', 200]);
    const links = result.rows;
    client.release();
    res.json(links);
  } catch (err) {
    console.error('Error executing query', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Endpoint to fetch links between pages
app.get('/api/links', async (req, res) => {
  try {
    const client = await pool.connect();
    const result = await client.query('SELECT from_page, to_page FROM crawldb.link WHERE is_searched = $1', [true]);

    const links = result.rows;
    client.release();
    res.json(links);
  } catch (err) {
    console.error('Error executing query', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Endpoint to fetch images
app.get('/api/images', async (req, res) => {
  try {
    const client = await pool.connect();
    const result = await client.query('SELECT page_id, filename, content_type FROM crawldb.image');
    const images = result.rows;
    client.release();
    res.json(images);
  } catch (err) {
    console.error('Error executing query', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
