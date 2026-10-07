<?php
// Isolated WordPress-function harness. No production credentials or network.
define('ABSPATH', __DIR__);
$GLOBALS['test_mode'] = 'demo';
$GLOBALS['test_cache'] = array();
function add_shortcode($name, $callback) { $GLOBALS['shortcode'] = $name; }
function add_action($name, $callback) {}
function get_option($key, $default = false) { return $key === 'sabga_leagues_mode' ? $GLOBALS['test_mode'] : $default; }
function get_transient($key) { return $GLOBALS['test_cache'][$key] ?? false; }
function set_transient($key, $value, $ttl) { $GLOBALS['test_cache'][$key] = $value; }
function delete_transient($key) { unset($GLOBALS['test_cache'][$key]); }
function is_wp_error($value) { return $value instanceof WP_Error; }
function shortcode_atts($defaults, $attributes, $name) { return array_merge($defaults, $attributes); }
function wp_enqueue_style(...$args) {}
function wp_enqueue_script(...$args) {}
function did_action($name) { return 1; }
function wp_style_is($handle, $state) { return true; }
function plugins_url($path, $file) { return '../sabga-leagues/' . $path; }
function rest_url($path) { return '/api/' . $path; }
function wp_unique_id($prefix) { static $i = 0; return $prefix . ++$i; }
function get_queried_object_id() { return 123; }
function esc_url($value) { return htmlspecialchars((string)$value, ENT_QUOTES); }
function esc_attr($value) { return htmlspecialchars((string)$value, ENT_QUOTES); }
function esc_html($value) { return htmlspecialchars((string)$value, ENT_QUOTES); }
function selected($a, $b) { if ((string)$a === (string)$b) echo 'selected="selected"'; }
function register_rest_route($namespace, $path, $args) { $GLOBALS['route'] = $args; }
function current_user_can($cap) { return false; }
function wp_die($message) { throw new RuntimeException($message); }
class WP_Error {
    private $code, $message, $data;
    function __construct($code, $message, $data = array()) { $this->code=$code; $this->message=$message; $this->data=$data; }
    function get_error_message() { return $this->message; }
    function get_error_code() { return $this->code; }
    function get_error_data() { return $this->data; }
}
class WP_REST_Response {
    public $data, $headers = array();
    function __construct($data) { $this->data = $data; }
    function header($name, $value) { $this->headers[$name] = $value; }
}
require __DIR__ . '/../sabga-leagues/sabga-leagues.php';
if (isset($argv[1]) && $argv[1] === '--render') {
    echo '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SABGA League Test</title><link rel="stylesheet" href="../sabga-leagues/assets/standings.css"></head><body style="margin:24px;background:#f5f5ef;font-family:Arial,sans-serif"><main style="max-width:1200px;margin:auto">';
    echo SABGA_Leagues::shortcode();
    echo '</main><script src="../sabga-leagues/assets/standings.js"></script></body></html>';
    exit;
}
if (isset($argv[1]) && $argv[1] === '--payload') {
    echo json_encode(SABGA_Leagues::payload((int)($argv[2] ?? 91)));
    exit;
}
$checks = 0;
function check($ok, $message) { global $checks; if (!$ok) throw new RuntimeException($message); $checks++; }
check($GLOBALS['shortcode'] === 'sabga_leagues', 'Shortcode registration');
check(count(SABGA_Leagues::groups()) === 11, '11 groups');
foreach (array(91, '101', 100) as $value) check(SABGA_Leagues::valid_group($value), 'Allowed group');
foreach (array('91 OR 1=1', 0, -91, 102, '91.0', null, array(91)) as $value) check(!SABGA_Leagues::valid_group($value), 'Reject invalid group');
foreach (array_keys(SABGA_Leagues::groups()) as $id) {
    $data = SABGA_Leagues::payload($id);
    check($data['group_id'] === $id && $data['mode'] === 'demo', 'Demo group payload');
    check(count($data['standings']) === 8, 'Demo rows');
}
$rows = SABGA_Leagues::payload(91)['standings'];
check($rows[0]['points_percentage'] > 80 && $rows[0]['points_percentage'] < 81, 'Points percent denominator');
check($rows[6]['average_pr'] === null, 'Missing PR preserved');
check($rows[7]['points_percentage'] === 0.0, 'Zero games no division error');
check($rows[7]['stats_available'] === false, 'Missing precomputed stats flag');
check(SABGA_Leagues::cell('average_pr', $rows[6]) === '—', 'Missing PR display');
check(SABGA_Leagues::cell('average_pr', array('average_pr'=>0)) === '0.00', 'Zero PR not missing');
$html = SABGA_Leagues::shortcode();
check(strpos($html, 'Demo · Fictional') !== false, 'Demo labelled');
check(strpos($html, 'name="page_id"') !== false, 'Plain permalinks fallback');
check(strpos($html, 'scope="col"') !== false && strpos($html, 'scope="row"') !== false, 'Table accessibility');
check(strpos(SABGA_Leagues::shortcode(array('group'=>'102')), 'Choose a valid') !== false, 'Invalid shortcode');
$_GET['sabga_group'] = '100';
check(strpos(SABGA_Leagues::shortcode(), '<h3 class="sabga-leagues__group">Guppy Group Blue') !== false, 'Group URL');
$_GET['sabga_group'] = array('91');
check(strpos(SABGA_Leagues::shortcode(), '<h3 class="sabga-leagues__group">A-League') !== false, 'Reject array query');
unset($_GET['sabga_group']);
$row = $rows[0]; $row['name'] = '<img src=x onerror=alert(1)>';
check(strpos(esc_html(SABGA_Leagues::cell('player', $row)), '<img') === false, 'Escape player names');
SABGA_Leagues::routes();
check($GLOBALS['route']['methods'] === 'GET', 'GET only');
$validate = $GLOBALS['route']['args']['group']['validate_callback'];
check(!$validate('102') && $validate('91'), 'REST group validation');
$request = new class { function get_param($name) { return 91; } };
$response = SABGA_Leagues::rest_standings($request);
check($response->headers['Cache-Control'] === 'no-store, max-age=0', 'Response cache header');
check(is_wp_error(SABGA_Leagues::payload(102)), 'Invalid payload error');
try { SABGA_Leagues::admin_action(); check(false, 'Admin denied'); }
catch (RuntimeException $e) { check(strpos($e->getMessage(), 'permission') !== false, 'Admin capability guard'); }
$GLOBALS['test_mode'] = 'live';
$missing = SABGA_Leagues::payload(91);
check($missing->get_error_code() === 'sabga_missing_config', 'Missing live config error');
define('SABGA_LEAGUES_DB_HOST','127.0.0.1');
define('SABGA_LEAGUES_DB_NAME','test_league');
define('SABGA_LEAGUES_DB_USER','readonly');
define('SABGA_LEAGUES_DB_PASSWORD','TEST_SECRET_DO_NOT_DISPLAY');
define('SABGA_LEAGUES_DB_PORT',1);
check(SABGA_Leagues::configured(), 'Config detection');
$key = SABGA_Leagues::cache_key(91);
set_transient($key, array('cached'=>true), 60);
check(SABGA_Leagues::payload(91) === array('cached'=>true), 'Cache hit does not connect');
$failure = SABGA_Leagues::payload(91, true);
check(is_wp_error($failure), 'Fresh connection bypasses cache');
check(strpos($failure->get_error_message(), 'TEST_SECRET') === false && strpos($failure->get_error_message(), '127.0.0.1') === false, 'No driver/credential leak');
$diagnostic = new ReflectionMethod('SABGA_Leagues', 'diagnostic');
$diagnostic->setAccessible(true);
foreach (array(1045,1044,1049,1142,1143,1146,1054,2002,2003,2005,2026,9999) as $code) {
    $exception = new PDOException('TEST_SECRET private host SQL text');
    $exception->errorInfo = array('HY000', $code, 'TEST_SECRET private driver text');
    $detail = $diagnostic->invoke(null, $exception, 'connection');
    check(strpos($detail, 'MySQL ' . $code) !== false, 'Diagnostic error number');
    check(strpos($detail, 'TEST_SECRET') === false && strpos($detail, 'private') === false, 'Diagnostic discards driver text');
}
$exception->errorInfo = array('SECRET_UNTRUSTED', 'SECRET_UNTRUSTED', 'TEST_SECRET');
check(strpos($diagnostic->invoke(null, $exception, 'standings query'), 'UNTRUSTED') === false, 'Invalid driver codes discarded');
check($failure->get_error_data() === array('status'=>503), 'Public error contains no diagnostics');
$last = new ReflectionProperty('SABGA_Leagues', 'last_diagnostic');
$last->setAccessible(true);
check(strpos($last->getValue(), 'Diagnostic: connection') !== false, 'Real connection failure recorded privately');
$GLOBALS['test_mode'] = 'demo';
SABGA_Leagues::payload(91);
check($last->getValue() === '', 'Each request resets diagnostic');
$summary = SABGA_Leagues::normalize_summary(array('total'=>45,'completed'=>6,'average_pr'=>5.47));
check($summary['outstanding'] === 39 && $summary['completed'] === 6, 'Summary counts');
check(abs($summary['percentage'] - 13.333333) < 0.001, 'Summary progress');
check(SABGA_Leagues::normalize_summary(array('total'=>0,'completed'=>0,'average_pr'=>null))['average_pr'] === null, 'Missing summary PR');
check(SABGA_Leagues::normalize_summary(array('total'=>0,'completed'=>0,'average_pr'=>null))['percentage'] === 0, 'Zero fixture summary');
check(SABGA_Leagues::payload(91)['deadline'] === '6 Dec 2026', 'Current deadline');
check(strpos(SABGA_Leagues::shortcode(), 'data-metric="progress"') !== false, 'Server summary markup');
echo "PASS: $checks PHP harness checks\n";
