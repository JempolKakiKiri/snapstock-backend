import express from 'express';
import multer from 'multer';
import { uploadNotes, getRecommendations } from '../controllers/inventoryController.js';

const router = express.Router();
const upload = multer({ storage: multer.memoryStorage() });

router.post('/notes/upload', upload.single('image'), uploadNotes);
router.get('/inventory/recommendations', getRecommendations);

export default router;
