
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('faq-search-input');
    const faqSections = document.querySelectorAll('.faq-category');
    const allDetails = document.querySelectorAll('details.accordion-005');

    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();

        allDetails.forEach(details => {
            const summaryText = details.querySelector('summary').textContent.toLowerCase();
            const bodyText = details.querySelector('.accordion-content').textContent.toLowerCase();
            const isMatch = summaryText.includes(searchTerm) || bodyText.includes(searchTerm);

            if (isMatch) {
                details.style.display = 'block';
                // Open match if searching
                if (searchTerm.length > 0) {
                    details.open = true;
                } else {
                    details.open = false;
                }
            } else {
                details.style.display = 'none';
                details.open = false;
            }
        });

        // Hide empty sections
        faqSections.forEach(section => {
            const visibleDetails = section.querySelectorAll('details.accordion-005[style="display: block;"], details.accordion-005:not([style*="display: none"])');
            if (visibleDetails.length === 0 && searchTerm.length > 0) {
                section.style.display = 'none';
            } else {
                section.style.display = 'block';
            }
        });
    });
});
