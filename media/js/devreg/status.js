define('preinstallTestPlan', [], function() {

    function init() {
        $('.upload-test-plan').fileUploader();
    }

    return {
        init: init
    };
});

if ($('#preinstall.devhub-form').length) {
    require('preinstallTestPLan').init();
}
