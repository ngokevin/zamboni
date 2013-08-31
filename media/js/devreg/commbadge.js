$(document).ready(function() {
    $(document.body).on('mouseover', '.account-links, .act-tray', function() {
        $('.account-links').addClass('active');
    }).on('mouseout', '.account-links', function() {
        $('.account-links').removeClass('active');
    }).on('click', '.account-links a', function() {
        $('.account-links').removeClass('active');
    }).on('mouseover', '.header-button.submit', function() {
        $('.account-links').removeClass('active');
    });
});
