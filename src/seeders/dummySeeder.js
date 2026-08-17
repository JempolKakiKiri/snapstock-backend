import { Product, Transaction, sequelize } from '../models/index.js';

const seedDatabase = async () => {
    try {
        await sequelize.authenticate();
        console.log('Database connection has been established successfully.');

        // Sync the database (creating tables if they don't exist)
        await sequelize.sync({ force: true }); // Warning: this drops existing tables!
        console.log('Database synced for seeding.');

        // 1. Create 3 Dummy Products
        const productsData = [
            { name: 'Beras Pandan Wangi 5kg', current_stock: 8, price: 65000, min_threshold: 10, max_threshold: 50 },
            { name: 'Minyak Goreng 2L', current_stock: 5, price: 35000, min_threshold: 15, max_threshold: 100 },
            { name: 'Gula Pasir 1kg', current_stock: 12, price: 15000, min_threshold: 20, max_threshold: 100 }
        ];

        const products = await Product.bulkCreate(productsData);
        console.log('Products created successfully.');

        // 2. Generate 30 days of randomized historical 'OUT' Transaction data
        const transactionsData = [];
        const today = new Date();

        for (const product of products) {
            for (let i = 0; i < 30; i++) {
                const transactionDate = new Date();
                transactionDate.setDate(today.getDate() - i);
                
                const hasSale = Math.random() > 0.3; // 70% chance of a sale

                if (hasSale) {
                    const quantitySold = Math.floor(Math.random() * 5) + 1; // Random qty between 1 and 5
                    
                    transactionsData.push({
                        product_id: product.id,
                        type: 'OUT',
                        quantity: quantitySold,
                        transaction_date: transactionDate
                    });
                }
            }
        }

        await Transaction.bulkCreate(transactionsData);
        console.log('30-day historical transactions created successfully.');

        console.log('Seeding completed successfully!');
        process.exit(0);
    } catch (error) {
        console.error('Error during seeding:', error);
        process.exit(1);
    }
};

seedDatabase();
