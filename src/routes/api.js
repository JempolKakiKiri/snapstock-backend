import express from 'express';
import multer from 'multer';
import {
  uploadNotes,
  getRecommendations,
  getTopRecommendations,
} from '../controllers/inventoryController.js';

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

router.post('/notes/upload', upload.single('image'), uploadNotes);
router.get('/inventory/recommendations', getRecommendations);
router.get('/inventory/top-recommendations', getTopRecommendations);

export default router;
