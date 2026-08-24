import axios from 'axios';
import FormData from 'form-data';
import { exec } from 'child_process';
import util from 'util';

const execPromise = util.promisify(exec);

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
    const dataStr = JSON.stringify(historicalData);
    const escapedDataStr = dataStr.replace(/'/g, "'\\''");

    const command = `cd ml/scripts && source venv/bin/activate && python3 inference_tsb.py '${escapedDataStr}'`;

    const { stdout } = await execPromise(command);

    const response = JSON.parse(stdout.trim());
    if (response.status === 'error') {
      throw new Error(response.message);
    }

    return response;
  } catch (error) {
    console.error('Error in predictRunout:', error.message);
    throw new Error('Failed to get prediction from ML Service');
  }
};
