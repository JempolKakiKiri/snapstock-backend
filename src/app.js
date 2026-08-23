import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import apiRoutes from './routes/api.js';
import { sequelize } from './models/index.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

app.use('/api', apiRoutes);

app.get('/', (req, res) => {
    res.send('Selamat datang di API Smart Restock UMKM!');
});

app.get('/api/health', (req, res) => {
    res.status(200).json({
        status: 'success',
        message: 'Smart Restock Backend is up and running!'
    });
});

sequelize.sync({ alter: true }).then(() => {
    console.log('Database synced successfully');
    app.listen(PORT, () => {
        console.log(`Server is running on http://localhost:${PORT}`);
    });
}).catch((err) => {
    console.error('Unable to connect to the database:', err);
});