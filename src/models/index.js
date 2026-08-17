import sequelize from '../config/database.js';
import Product from './Product.js';
import Transaction from './Transaction.js';

Product.hasMany(Transaction, { foreignKey: 'product_id', as: 'transactions' });
Transaction.belongsTo(Product, { foreignKey: 'product_id', as: 'product' });

export {
    sequelize,
    Product,
    Transaction
};
