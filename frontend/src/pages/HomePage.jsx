import React, { useState, useEffect } from 'react';
import FileUpload from '../components/FileUpload/FileUpload';
import { uploadService } from '../services/uploadService';

const HomePage = () => {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      const data = await uploadService.getDatasets();
      setDatasets(data);
    } catch (error) {
      console.error('Failed to load datasets:', error);
      showNotification('Failed to load datasets', 'error');
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleUploadSuccess = (result) => {
    showNotification(`Dataset "${result.filename}" uploaded successfully!`, 'success');
    loadDatasets(); // Refresh the list
  };

  const handleUploadError = (error) => {
    showNotification('Upload failed. Please try again.', 'error');
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  return (
    <div className="home-page">
      {notification && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
        </div>
      )}
      
      <FileUpload 
        onUploadSuccess={handleUploadSuccess}
        onUploadError={handleUploadError}
      />
      
      {datasets.length > 0 && (
        <div className="datasets-list">
          <h3>Uploaded Datasets</h3>
          <div className="datasets-grid">
            {datasets.map((dataset) => (
              <div key={dataset.id} className="dataset-card">
                <h4>{dataset.filename}</h4>
                <p className="description">{dataset.description}</p>
                <div className="dataset-meta">
                  <span>Type: {dataset.file_type}</span>
                  <span>Size: {(dataset.file_size / 1024).toFixed(1)} KB</span>
                  <span>Uploaded: {new Date(dataset.upload_date).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;
