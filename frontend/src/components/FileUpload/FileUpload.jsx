import React, { useState, useRef } from 'react';
import { uploadService } from '../../services/uploadService';
import './FileUpload.css';

const FileUpload = ({ onUploadSuccess, onUploadError }) => {
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState({});
  const [uploadProgress, setUploadProgress] = useState(0);
  
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // Supported file types
  const supportedTypes = ['.csv', '.xlsx', '.xls', '.json', '.tsv'];
  const maxFileSize = 100 * 1024 * 1024; // 100MB

  const validateFile = (selectedFile) => {
    const newErrors = {};
    
    if (!selectedFile) {
      newErrors.file = 'Please select a file';
      setErrors(newErrors);
      return false;
    }

    // Check file type
    const fileName = selectedFile.name.toLowerCase();
    const isValidType = supportedTypes.some(type => fileName.endsWith(type));
    
    if (!isValidType) {
      newErrors.file = `Unsupported file type. Please upload: ${supportedTypes.join(', ')}`;
    }

    // Check file size
    if (selectedFile.size > maxFileSize) {
      newErrors.file = 'File size exceeds 100MB limit';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateDescription = (desc) => {
    const newErrors = {};
    
    if (!desc.trim()) {
      newErrors.description = 'Description is required';
    } else if (desc.trim().length < 10) {
      newErrors.description = 'Description must be at least 10 characters';
    } else if (desc.length > 1000) {
      newErrors.description = 'Description must not exceed 1000 characters';
    }

    setErrors(prev => ({ ...prev, ...newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
      setErrors(prev => ({ ...prev, file: null }));
    }
  };

  const handleDescriptionChange = (e) => {
    const value = e.target.value;
    setDescription(value);
    
    // Clear error when user starts typing
    if (errors.description && value.trim().length >= 10) {
      setErrors(prev => ({ ...prev, description: null }));
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && validateFile(droppedFile)) {
      setFile(droppedFile);
      setErrors(prev => ({ ...prev, file: null }));
    }
  };

  const handleUpload = async () => {
    // Validate both file and description
    const isFileValid = validateFile(file);
    const isDescValid = validateDescription(description);
    
    if (!isFileValid || !isDescValid) {
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      const result = await uploadService.uploadDataset(file, description);
      
      // Reset form
      setFile(null);
      setDescription('');
      setErrors({});
      setUploadProgress(0);
      
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Notify parent component
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }

    } catch (error) {
      console.error('Upload failed:', error);
      
      let errorMessage = 'Upload failed. Please try again.';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setErrors({ upload: errorMessage });
      
      if (onUploadError) {
        onUploadError(error);
      }
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="file-upload-container">
      <h2>Upload Dataset</h2>
      
      {/* File Drop Zone */}
      <div
        ref={dropZoneRef}
        className={`drop-zone ${dragActive ? 'drag-active' : ''} ${errors.file ? 'error' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <div className="drop-zone-content">
          {file ? (
            <div className="file-info">
              <div className="file-icon">📄</div>
              <div className="file-details">
                <p className="file-name">{file.name}</p>
                <p className="file-size">{formatFileSize(file.size)}</p>
              </div>
              <button
                type="button"
                className="remove-file-btn"
                onClick={() => {
                  setFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
              >
                ✕
              </button>
            </div>
          ) : (
            <>
              <div className="upload-icon">⬆️</div>
              <p>Drag and drop your dataset here</p>
              <p className="or-text">or</p>
              <button
                type="button"
                className="browse-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Browse Files
              </button>
            </>
          )}
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          accept={supportedTypes.join(',')}
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
      </div>
      
      {errors.file && <div className="error-message">{errors.file}</div>}
      
      <div className="supported-formats">
        <p>Supported formats: {supportedTypes.join(', ')}</p>
        <p>Maximum file size: 100MB</p>
      </div>

      {/* Description Input */}
      <div className="description-section">
        <label htmlFor="description">Dataset Description *</label>
        <textarea
          id="description"
          value={description}
          onChange={handleDescriptionChange}
          placeholder="Describe your dataset... (minimum 10 characters)"
          className={errors.description ? 'error' : ''}
          rows={4}
          maxLength={1000}
        />
        <div className="char-counter">
          {description.length}/1000 characters
        </div>
        {errors.description && <div className="error-message">{errors.description}</div>}
      </div>

      {/* Upload Progress */}
      {uploading && (
        <div className="progress-bar-container">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <span className="progress-text">{uploadProgress}%</span>
        </div>
      )}

      {/* Error Display */}
      {errors.upload && (
        <div className="error-message upload-error">{errors.upload}</div>
      )}

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={uploading || !file || !description.trim()}
        className={`upload-btn ${uploading ? 'uploading' : ''}`}
      >
        {uploading ? 'Uploading...' : 'Upload Dataset'}
      </button>
    </div>
  );
};

export default FileUpload;
