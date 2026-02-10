import { render, screen } from '@testing-library/react';
import Card from './Card';

describe('Card', () => {
    it('renders children correctly', () => {
        render(<Card><div>Card Content</div></Card>);
        expect(screen.getByText('Card Content')).toBeInTheDocument();
    });

    it('applies custom className', () => {
        render(<Card className="custom-class">Content</Card>);
        // Note: We need to find the card element. Since Card renders a div with class 'card',
        // we can look for the text and check its parent or use a test id.
        // Here we'll just check if the text is there, and we assume the class is applied if the component renders.
        // For more robust testing, we could add data-testid to Card.
        const content = screen.getByText('Content');
        expect(content.parentElement).toHaveClass('custom-class');
    });
});
