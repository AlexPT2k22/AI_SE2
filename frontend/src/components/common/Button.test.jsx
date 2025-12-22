import { render, screen, fireEvent } from '@testing-library/react';
import Button from './Button';
import { vi } from 'vitest';

describe('Button', () => {
 it('renders children correctly', () => {
 render(<Button>Click me</Button>);
 expect(screen.getByText('Click me')).toBeInTheDocument();
 });

 it('calls onClick handler when clicked', () => {
 const handleClick = vi.fn();
 render(<Button onClick={handleClick}>Click me</Button>);
 fireEvent.click(screen.getByText('Click me'));
 expect(handleClick).toHaveBeenCalledTimes(1);
 });

 it('applies variant classes', () => {
 render(<Button variant="secondary">Secondary</Button>);
 const button = screen.getByText('Secondary');
 expect(button).toHaveClass('btn-secondary');
 });

 it('is disabled when disabled prop is true', () => {
 render(<Button disabled>Disabled</Button>);
 const button = screen.getByText('Disabled');
 expect(button).toBeDisabled();
 });
});
