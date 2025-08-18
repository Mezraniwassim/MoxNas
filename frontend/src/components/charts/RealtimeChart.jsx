import React, { useRef, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Box, Paper, Typography, useTheme } from '@mui/material';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const RealtimeChart = ({
  title,
  data,
  height = 300,
  maxDataPoints = 20,
  showLegend = true,
  showGrid = true,
  animate = true,
  yAxisMax = 100,
  yAxisLabel = '',
  colors = ['#1976d2', '#dc004e', '#ed6c02', '#2e7d32'],
}) => {
  const theme = useTheme();
  const chartRef = useRef();

  const chartData = {
    labels: data.labels || [],
    datasets: (data.datasets || []).map((dataset, index) => ({
      label: dataset.label,
      data: dataset.data,
      borderColor: colors[index % colors.length],
      backgroundColor: `${colors[index % colors.length]}20`,
      borderWidth: 2,
      fill: dataset.fill || false,
      tension: 0.4,
      pointRadius: 2,
      pointHoverRadius: 4,
      pointBackgroundColor: colors[index % colors.length],
      pointBorderColor: '#fff',
      pointBorderWidth: 1,
    })),
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: animate ? {
      duration: 750,
      easing: 'easeInOutQuart',
    } : false,
    plugins: {
      legend: {
        display: showLegend,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 20,
          color: theme.palette.text.primary,
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: theme.palette.background.paper,
        titleColor: theme.palette.text.primary,
        bodyColor: theme.palette.text.primary,
        borderColor: theme.palette.divider,
        borderWidth: 1,
        cornerRadius: 8,
        padding: 12,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            label += context.parsed.y;
            if (yAxisLabel) {
              label += ` ${yAxisLabel}`;
            }
            return label;
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        grid: {
          display: showGrid,
          color: theme.palette.divider,
          drawBorder: false,
        },
        ticks: {
          color: theme.palette.text.secondary,
          maxTicksLimit: 8,
          font: {
            size: 11,
          },
        },
      },
      y: {
        display: true,
        beginAtZero: true,
        max: yAxisMax,
        grid: {
          display: showGrid,
          color: theme.palette.divider,
          drawBorder: false,
        },
        ticks: {
          color: theme.palette.text.secondary,
          callback: function(value) {
            return value + (yAxisLabel ? ` ${yAxisLabel}` : '');
          },
          font: {
            size: 11,
          },
        },
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
    elements: {
      point: {
        hoverRadius: 6,
      },
    },
  };

  useEffect(() => {
    const chart = chartRef.current;
    if (chart) {
      chart.update('none');
    }
  }, [data]);

  return (
    <Paper elevation={1} sx={{ p: 2, height: height + 80 }}>
      {title && (
        <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>
          {title}
        </Typography>
      )}
      <Box height={height}>
        <Line ref={chartRef} data={chartData} options={options} />
      </Box>
    </Paper>
  );
};

export default RealtimeChart;