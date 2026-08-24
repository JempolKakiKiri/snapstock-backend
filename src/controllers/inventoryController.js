import { Product, Transaction, sequelize } from '../models/index.js';
import { parseNotesImage, predictRunout } from '../services/mlService.js';
import { Op } from 'sequelize';

export const uploadNotes = async (req, res) => {
  try {
    if (!req.file) {
      return res
        .status(400)
        .json({ status: 'error', message: 'No image file provided' });
    }

    const mlResponse = await parseNotesImage(
      req.file.buffer,
      req.file.originalname
    );

    if (!mlResponse || !mlResponse.items) {
      return res
        .status(500)
        .json({ status: 'error', message: 'Invalid response from ML service' });
    }

    const items = mlResponse.items;
    const processedItems = [];

    for (const item of items) {
      const qty = item.qty || 1;
      const price = item.harga || 0;

      const [product, created] = await Product.findOrCreate({
        where: { name: item.nama },
        defaults: {
          price: price,
          current_stock: qty,
        },
      });

      if (!created) {
        product.current_stock += qty;
        await product.save();
      }

      await Transaction.create({
        product_id: product.id,
        type: 'IN',
        quantity: qty,
        transaction_date: new Date(),
      });

      processedItems.push({
        ...product.toJSON(),
        receipt_qty: qty,
      });
    }

    res.status(200).json({
      status: 'success',
      message: 'Notes processed successfully',
      data: processedItems,
    });
  } catch (error) {
    console.error('Upload Notes Error:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Internal server error',
    });
  }
};

export const getRecommendations = async (req, res) => {
  try {
    const lowStockProducts = await Product.findAll({
      where: sequelize.where(
        sequelize.col('current_stock'),
        '<=',
        sequelize.col('min_threshold')
      ),
    });

    if (lowStockProducts.length === 0) {
      return res.status(200).json({
        status: 'success',
        message: 'No products currently need restocking.',
        data: [],
      });
    }

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const recommendations = [];

    for (const product of lowStockProducts) {
      const transactions = await Transaction.findAll({
        where: {
          product_id: product.id,
          type: 'OUT',
          transaction_date: {
            [Op.gte]: thirtyDaysAgo,
          },
        },
        order: [['transaction_date', 'ASC']],
      });

      const historicalData = transactions.map((t) => ({
        date: t.transaction_date.toISOString(),
        qty: t.quantity,
      }));

      let runout_days = null;
      if (historicalData.length > 0) {
        const mlResponse = await predictRunout({
          product_id: product.id,
          product_name: product.name,
          current_stock: product.current_stock,
          history: historicalData,
        });
        runout_days =
          mlResponse.runout_days || mlResponse.runout_days === 0
            ? mlResponse.runout_days
            : null;
      } else {
        runout_days = 0;
      }

      const recommended_restock_qty =
        product.max_threshold - product.current_stock;

      recommendations.push({
        product_id: product.id,
        name: product.name,
        current_stock: product.current_stock,
        runout_days: runout_days,
        recommended_restock_qty:
          recommended_restock_qty > 0 ? recommended_restock_qty : 0,
      });
    }

    res.status(200).json({
      status: 'success',
      data: recommendations,
    });
  } catch (error) {
    console.error('Recommendations Error:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Internal server error',
    });
  }
};

export const getTopRecommendations = async (req, res) => {
  try {
    const topProducts = await Product.findAll({
      where: sequelize.where(
        sequelize.col('current_stock'),
        '<=',
        sequelize.col('min_threshold')
      ),
      order: [
        ['current_stock', 'ASC'],
        ['min_threshold', 'DESC'],
      ],
      limit: 5,
    });

    if (topProducts.length === 0) {
      return res.status(200).json({
        status: 'success',
        message: 'No products currently need restocking.',
        data: [],
      });
    }

    const thirtyDaysAgo = new Date();
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    const recommendations = [];

    for (const product of topProducts) {
      const transactions = await Transaction.findAll({
        where: {
          product_id: product.id,
          type: 'OUT',
          transaction_date: {
            [Op.gte]: thirtyDaysAgo,
          },
        },
        order: [['transaction_date', 'ASC']],
      });

      const historicalData = transactions.map((t) => ({
        date: t.transaction_date.toISOString(),
        qty: t.quantity,
      }));

      let runout_days = null;
      if (historicalData.length > 0) {
        const mlResponse = await predictRunout({
          product_id: product.id,
          product_name: product.name,
          current_stock: product.current_stock,
          history: historicalData,
        });
        runout_days =
          mlResponse.runout_days || mlResponse.runout_days === 0
            ? mlResponse.runout_days
            : null;
      } else {
        runout_days = 0;
      }

      const recommended_restock_qty =
        product.max_threshold - product.current_stock;

      recommendations.push({
        product_id: product.id,
        name: product.name,
        current_stock: product.current_stock,
        runout_days: runout_days,
        recommended_restock_qty:
          recommended_restock_qty > 0 ? recommended_restock_qty : 0,
      });
    }

    res.status(200).json({
      status: 'success',
      data: recommendations,
    });
  } catch (error) {
    console.error('Top Recommendations Error:', error);
    res.status(500).json({
      status: 'error',
      message: error.message || 'Internal server error',
    });
  }
};
