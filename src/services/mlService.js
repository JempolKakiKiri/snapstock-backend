import axios from 'axios';
import FormData from 'form-data';

export const parseNotesImage = async (fileBuffer, originalName) => {
  try {
    const formData = new FormData();
    formData.append('image', fileBuffer, originalName);

    console.log('Sending request to ML_PARSER_URL:', process.env.ML_PARSER_URL);
    const response = await axios.post(process.env.ML_PARSER_URL, formData, {
      headers: {
        ...formData.getHeaders(),
      },
    });

    return response.data;
  } catch (error) {
    console.error('Error in parseNotesImage:', error.message);
    console.error('Response data:', error.response?.data);
    throw new Error('Failed to parse notes from ML Service');
  }
};

export const predictRunout = async (historicalData) => {
  try {
    const response = await axios.post(process.env.ML_PREDICT_URL, {
      data: historicalData,
    });

    return response.data;
  } catch (error) {
    console.error('Error in predictRunout:', error.message);
    throw new Error('Failed to get prediction from ML Service');
  }
};
