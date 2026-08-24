import { Product, Transaction, sequelize } from '../models/index.js';

const seed = async () => {
  try {
    await sequelize.sync();
    console.log(
      'Database connected. Membersihkan riwayat transaksi OUT lama...'
    );
    await Transaction.destroy({ where: { type: 'OUT' } });

    const products = await Product.findAll();
    const today = new Date();

    console.log(
      `Membuat data transaksi sintetis 30 hari terakhir untuk ${products.length} barang...`
    );

    let totalTransactions = 0;

    for (const product of products) {
      const numTransactions = Math.floor(Math.random() * 15) + 10;

      for (let i = 0; i < numTransactions; i++) {
        const randomDaysAgo = Math.floor(Math.random() * 30);
        const date = new Date(today);
        date.setDate(date.getDate() - randomDaysAgo);

        const randomQty = Math.floor(Math.random() * 5) + 1;

        await Transaction.create({
          product_id: product.id,
          type: 'OUT',
          quantity: randomQty,
          transaction_date: date,
        });
        totalTransactions++;
      }
    }
    console.log(
      `Selesai! Berhasil membuat ${totalTransactions} transaksi sintetis.`
    );
    process.exit(0);
  } catch (error) {
    console.error('Seeding error:', error);
    process.exit(1);
  }
};

seed();
