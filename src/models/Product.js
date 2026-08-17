import { DataTypes } from 'sequelize';
import sequelize from '../config/database.js';

const Product = sequelize.define('Product', {
    id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true
    },
    name: {
        type: DataTypes.STRING,
        allowNull: false
    },
    current_stock: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 0
    },
    price: {
        type: DataTypes.DECIMAL(10, 2),
        allowNull: false
    },
    min_threshold: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 10
    },
    max_threshold: {
        type: DataTypes.INTEGER,
        allowNull: false,
        defaultValue: 50
    }
}, {
    tableName: 'Products',
    timestamps: true
});

export default Product;
