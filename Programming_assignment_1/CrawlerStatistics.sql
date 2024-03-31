-- Number of Sites
SELECT COUNT(DISTINCT domain) AS num_sites FROM crawldb.site;

-- Number of Web Pages
SELECT COUNT(*) AS num_web_pages FROM crawldb.page;

-- Number of Duplicates
SELECT COUNT(*) AS num_duplicates
FROM (
    SELECT url
    FROM crawldb.page
    GROUP BY url
    HAVING COUNT(*) > 1
) AS duplicates;

-- Number of Binary Documents
SELECT data_type_code, COUNT(*) AS num_documents
FROM crawldb.page_data
WHERE data_type_code IN ('PDF', 'DOC', 'DOCX', 'PPT', 'PPTX')
GROUP BY data_type_code;

-- Number of Images
SELECT COUNT(*) AS num_images FROM crawldb.image;

-- Average Number of Images per Web Page
SELECT AVG(num_images) AS avg_images_per_page
FROM (
    SELECT page_id, COUNT(*) AS num_images
    FROM crawldb.image
    GROUP BY page_id
) AS image_counts;
