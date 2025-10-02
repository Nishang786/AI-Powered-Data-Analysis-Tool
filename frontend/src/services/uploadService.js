import { apiClient } from './api';

export const uploadService = {
  /**
   * Upload a dataset file with description
   */
  uploadDataset: async (file, description) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('description', description);

    try {
      const response = await apiClient.post('/upload/dataset', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          // You can use this for progress bar
          console.log(`Upload Progress: ${percentCompleted}%`);
        },
      });
      return response.data;
    } catch (error) {
      console.error('Upload failed:', error);
      throw error;
    }
  },

  /**
   * Get list of all datasets
   */
  getDatasets: async () => {
    try {
      const response = await apiClient.get('/upload/datasets');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch datasets:', error);
      throw error;
    }
  },

  /**
   * Get dataset information by ID
   */
  getDatasetInfo: async (datasetId) => {
    try {
      const response = await apiClient.get(`/upload/dataset/${datasetId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch dataset info:', error);
      throw error;
    }
  },

  /**
   * Delete a dataset
   */
  deleteDataset: async (datasetId) => {
    try {
      const response = await apiClient.delete(`/upload/dataset/${datasetId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to delete dataset:', error);
      throw error;
    }
  },
};
