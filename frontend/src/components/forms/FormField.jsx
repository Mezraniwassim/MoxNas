import React from 'react';
import {
  TextField,
  FormControl,
  FormLabel,
  FormControlLabel,
  Switch,
  Checkbox,
  Select,
  MenuItem,
  InputLabel,
  RadioGroup,
  Radio,
  Slider,
  Typography,
  Box,
  FormHelperText,
  Chip,
} from '@mui/material';
import { useField } from 'formik';

const FormField = ({
  name,
  label,
  type = 'text',
  options = [],
  helperText,
  disabled = false,
  required = false,
  fullWidth = true,
  size = 'medium',
  multiline = false,
  rows = 4,
  placeholder,
  min,
  max,
  step,
  multiple = false,
  ...props
}) => {
  const [field, meta, helpers] = useField(name);
  const { setValue, setTouched } = helpers;

  const hasError = meta.touched && !!meta.error;
  const errorMessage = hasError ? meta.error : helperText;

  const handleChange = (event) => {
    const value = event.target.value;
    setValue(value);
  };

  const handleBlur = () => {
    setTouched(true);
  };

  const renderTextField = () => (
    <TextField
      {...field}
      {...props}
      label={label}
      type={type}
      error={hasError}
      helperText={errorMessage}
      disabled={disabled}
      required={required}
      fullWidth={fullWidth}
      size={size}
      multiline={multiline}
      rows={multiline ? rows : undefined}
      placeholder={placeholder}
      inputProps={{
        min: type === 'number' ? min : undefined,
        max: type === 'number' ? max : undefined,
        step: type === 'number' ? step : undefined,
      }}
    />
  );

  const renderSelect = () => (
    <FormControl fullWidth={fullWidth} size={size} error={hasError} required={required}>
      <InputLabel>{label}</InputLabel>
      <Select
        {...field}
        label={label}
        disabled={disabled}
        multiple={multiple}
        onChange={handleChange}
        onBlur={handleBlur}
        renderValue={multiple ? (selected) => (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
            {selected.map((value) => {
              const option = options.find(opt => opt.value === value);
              return (
                <Chip
                  key={value}
                  label={option?.label || value}
                  size="small"
                />
              );
            })}
          </Box>
        ) : undefined}
      >
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
      {errorMessage && <FormHelperText>{errorMessage}</FormHelperText>}
    </FormControl>
  );

  const renderRadioGroup = () => (
    <FormControl component="fieldset" error={hasError} required={required}>
      <FormLabel component="legend">{label}</FormLabel>
      <RadioGroup
        {...field}
        onChange={handleChange}
        onBlur={handleBlur}
      >
        {options.map((option) => (
          <FormControlLabel
            key={option.value}
            value={option.value}
            control={<Radio />}
            label={option.label}
            disabled={disabled || option.disabled}
          />
        ))}
      </RadioGroup>
      {errorMessage && <FormHelperText>{errorMessage}</FormHelperText>}
    </FormControl>
  );

  const renderCheckbox = () => (
    <FormControl error={hasError}>
      <FormControlLabel
        control={
          <Checkbox
            {...field}
            checked={field.value || false}
            onChange={(event) => setValue(event.target.checked)}
            onBlur={handleBlur}
            disabled={disabled}
            color="primary"
          />
        }
        label={label}
      />
      {errorMessage && <FormHelperText>{errorMessage}</FormHelperText>}
    </FormControl>
  );

  const renderSwitch = () => (
    <FormControl error={hasError}>
      <FormControlLabel
        control={
          <Switch
            {...field}
            checked={field.value || false}
            onChange={(event) => setValue(event.target.checked)}
            onBlur={handleBlur}
            disabled={disabled}
            color="primary"
          />
        }
        label={label}
      />
      {errorMessage && <FormHelperText>{errorMessage}</FormHelperText>}
    </FormControl>
  );

  const renderSlider = () => (
    <FormControl fullWidth={fullWidth} error={hasError}>
      <Typography gutterBottom>{label}</Typography>
      <Slider
        {...field}
        value={field.value || 0}
        onChange={(event, value) => setValue(value)}
        onBlur={handleBlur}
        disabled={disabled}
        min={min || 0}
        max={max || 100}
        step={step || 1}
        valueLabelDisplay="auto"
        marks={props.marks}
      />
      {errorMessage && <FormHelperText>{errorMessage}</FormHelperText>}
    </FormControl>
  );

  const renderPassword = () => (
    <TextField
      {...field}
      {...props}
      label={label}
      type="password"
      error={hasError}
      helperText={errorMessage}
      disabled={disabled}
      required={required}
      fullWidth={fullWidth}
      size={size}
      placeholder={placeholder}
      autoComplete="off"
    />
  );

  const renderTextarea = () => (
    <TextField
      {...field}
      {...props}
      label={label}
      error={hasError}
      helperText={errorMessage}
      disabled={disabled}
      required={required}
      fullWidth={fullWidth}
      size={size}
      multiline
      rows={rows}
      placeholder={placeholder}
    />
  );

  switch (type) {
    case 'select':
      return renderSelect();
    case 'radio':
      return renderRadioGroup();
    case 'checkbox':
      return renderCheckbox();
    case 'switch':
      return renderSwitch();
    case 'slider':
      return renderSlider();
    case 'password':
      return renderPassword();
    case 'textarea':
      return renderTextarea();
    case 'text':
    case 'email':
    case 'number':
    case 'url':
    case 'tel':
    case 'date':
    case 'time':
    case 'datetime-local':
    default:
      return renderTextField();
  }
};

export default FormField;