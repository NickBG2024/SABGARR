<?php
if (!defined('ABSPATH')) { exit; }

final class SABGA_Leagues {
    const VERSION = '0.1.2';
    private static $last_diagnostic = '';
    const CACHE_SECONDS = 60;
    private static $plugin_file;

    public static function boot($file) {
        self::$plugin_file = $file;
        add_shortcode('sabga_leagues', array(__CLASS__, 'shortcode'));
        add_action('wp_enqueue_scripts', array(__CLASS__, 'page_assets'));
        add_action('rest_api_init', array(__CLASS__, 'routes'));
        add_action('admin_menu', array(__CLASS__, 'admin_menu'));
        add_action('admin_post_sabga_leagues_action', array(__CLASS__, 'admin_action'));
    }

    public static function groups() {
        // Source: SABGARRLive.py, 2026 Series 4, SeriesID 13.
        return array(91 => 'A-League', 92 => 'B-League', 93 => 'C-League',
            94 => 'D-League', 95 => 'E-League', 96 => 'F-League', 97 => 'G-League',
            98 => 'Guppy Group Yellow', 100 => 'Guppy Group Blue',
            99 => 'Guppy Group Red', 101 => 'Guppy Group Green');
    }

    public static function mode() {
        return get_option('sabga_leagues_mode', 'demo') === 'live' ? 'live' : 'demo';
    }

    public static function valid_group($value) {
        return is_scalar($value) && preg_match('/^[0-9]+$/D', (string) $value)
            && isset(self::groups()[(int) $value]);
    }

    public static function configured() {
        foreach (array('HOST', 'NAME', 'USER', 'PASSWORD') as $key) {
            $name = 'SABGA_LEAGUES_DB_' . $key;
            if (!defined($name) || !is_string(constant($name)) || constant($name) === '') {
                return false;
            }
        }
        return true;
    }

    public static function cache_key($id) {
        $config = array();
        foreach (array('HOST', 'NAME', 'USER', 'PASSWORD', 'PORT', 'SSL_CA') as $key) {
            $name = 'SABGA_LEAGUES_DB_' . $key;
            $config[] = defined($name) ? constant($name) : '';
        }
        return 'sabga_lg_' . md5(self::VERSION . serialize($config)) . '_' . (int) $id;
    }

    public static function standings_sql() {
        // Preserve display_cached_matchtype_standings ordering, including NULL ordering.
        // The league database is never written to by this plugin.
        return 'SELECT p.PlayerID AS player_id, p.Name AS name, p.Nickname AS nickname,
            IFNULL(s.GamesPlayed, 0) AS played, IFNULL(s.Wins, 0) AS wins,
            IFNULL(s.Losses, 0) AS losses, IFNULL(s.Points, 0) AS points,
            IFNULL(s.WinPercentage, 0) AS win_percentage, IFNULL(s.PRWins, 0) AS pr_wins,
            s.AveragePR AS average_pr, s.AverageLuck AS average_luck,
            IFNULL(s.HeadToHeadScore, 0) AS h2h, s.PlayerID AS stats_player_id
            FROM (
                SELECT DISTINCT p.PlayerID, p.Name, p.Nickname
                FROM Players p
                JOIN Fixtures f ON (f.Player1ID = p.PlayerID OR f.Player2ID = p.PlayerID)
                WHERE f.MatchTypeID = ?
            ) p
            LEFT JOIN MatchTypePlayerStats s ON s.PlayerID = p.PlayerID AND s.MatchTypeID = ?
            ORDER BY s.Points DESC, s.Wins DESC, s.PRWins DESC,
                s.HeadToHeadScore DESC, s.AveragePR ASC, s.GamesPlayed DESC';
    }

    public static function normalize($rows) {
        $result = array();
        foreach ($rows as $i => $row) {
            $played = (int) $row['played'];
            $points = (int) $row['points'];
            $result[] = array(
                'position' => $i + 1,
                'name' => (string) $row['name'], 'nickname' => (string) ($row['nickname'] ?? ''),
                'played' => $played, 'points' => $points,
                'points_percentage' => $played > 0 ? $points / ($played * 3) * 100 : 0.0,
                'wins' => (int) $row['wins'], 'pr_wins' => (int) $row['pr_wins'],
                'h2h' => (int) $row['h2h'], 'losses' => (int) $row['losses'],
                'win_percentage' => (float) $row['win_percentage'],
                'average_pr' => $row['average_pr'] === null ? null : (float) $row['average_pr'],
                'average_luck' => $row['average_luck'] === null ? null : (float) $row['average_luck'],
                'stats_available' => $row['stats_player_id'] !== null,
            );
        }
        return $result;
    }

    private static function demo_rows() {
        // Fictional people and values. Preordered to match the live sorting rules.
        $values = array(
            array('Demo Player One', 'example1', 7, 17, 6, 5, 0, 1, 85.7143, 6.12, -0.08),
            array('Demo Player Two', 'example2', 7, 15, 5, 5, 0, 2, 71.4286, 6.58, 0.12),
            array('Demo Player Three', 'example3', 6, 12, 4, 4, 1, 2, 66.6667, 7.05, -0.14),
            array('Demo Player Four', 'example4', 6, 12, 4, 4, 0, 2, 66.6667, 6.83, 0.21),
            array('Demo Player Five', 'example5', 5, 8, 3, 2, 0, 2, 60, 8.41, 0.02),
            array('Demo Player Six', 'example6', 4, 5, 2, 1, 0, 2, 50, 9.2, -0.3),
            array('Demo Player Seven', 'example7', 2, 2, 1, 0, 0, 1, 50, null, null),
            array('Demo Player Eight', 'example8', 0, 0, 0, 0, 0, 0, 0, null, null),
        );
        $keys = array('name', 'nickname', 'played', 'points', 'wins', 'pr_wins', 'h2h',
            'losses', 'win_percentage', 'average_pr', 'average_luck');
        $rows = array();
        foreach ($values as $i => $value) {
            $row = array_combine($keys, $value);
            $row['stats_player_id'] = $i === 7 ? null : $i + 1;
            $rows[] = $row;
        }
        return $rows;
    }

    // Only fixed guidance and validated numeric codes are retained; never driver messages.
    private static function diagnostic($error, $stage) {
        $info = $error instanceof PDOException && is_array($error->errorInfo) ? $error->errorInfo : array();
        $state = isset($info[0]) && preg_match('/^[A-Z0-9]{5}$/D', (string) $info[0]) ? $info[0] : 'unknown';
        $code = isset($info[1]) && is_numeric($info[1]) ? (int) $info[1] : 0;
        $help = array(
            1045 => 'Authentication rejected. Check the RO username and its reset password in wp-config.php; confirm the account can connect from this WordPress server.',
            1044 => 'Database access denied. Check that the RO account has access to the configured league database.',
            1049 => 'Database not found. Check the league database name in wp-config.php.',
            1142 => 'Table access denied. The RO account needs SELECT permission on Players, Fixtures and MatchTypePlayerStats.',
            1143 => 'Column access denied. The RO account needs SELECT permission on the standings columns.',
            1146 => 'A required table is missing. Confirm Players, Fixtures and MatchTypePlayerStats exist in the configured database with exactly that letter casing.',
            1054 => 'A standings column is missing. Confirm this database has the same table structure as the live Streamlit database.',
            2002 => 'Database connection failed. Verify the league hostname and port; ask Xneelo whether this WordPress server can reach the database.',
            2003 => 'Database server could not be reached. Check the hostname, port and hosting connection restrictions.',
            2005 => 'Database hostname could not be resolved. Check the league hostname in wp-config.php.',
            2026 => 'Database TLS connection failed. Ask Xneelo about the required TLS settings and CA certificate.',
        );
        $guidance = $help[$code] ?? 'The database operation failed. Share this diagnostic code so we can check the next step.';
        return 'Diagnostic: ' . $stage . '; SQLSTATE ' . $state . '; MySQL ' . ($code ?: 'unknown') . '. ' . $guidance;
    }

    public static function payload($id, $fresh = false) {
        self::$last_diagnostic = '';
        if (!self::valid_group($id)) {
            return new WP_Error('sabga_invalid_group', 'Choose a valid current league group.', array('status' => 400));
        }
        $id = (int) $id;
        if (self::mode() === 'demo') {
            return self::wrap($id, self::demo_rows(), 'demo');
        }
        if (!self::configured()) {
            return new WP_Error('sabga_missing_config', 'Live standings are not configured yet.', array('status' => 503));
        }
        $key = self::cache_key($id);
        if (!$fresh) {
            $cached = get_transient($key);
            if (is_array($cached)) { return $cached; }
        }
        if (!class_exists('PDO') || !in_array('mysql', PDO::getAvailableDrivers(), true)) {
            return new WP_Error('sabga_driver', 'The server needs the PHP PDO MySQL extension.', array('status' => 503));
        }
        $port = defined('SABGA_LEAGUES_DB_PORT') ? (int) SABGA_LEAGUES_DB_PORT : 3306;
        if ($port < 1 || $port > 65535 || preg_match('/[;\x00-\x1f]/', SABGA_LEAGUES_DB_HOST . SABGA_LEAGUES_DB_NAME)) {
            return new WP_Error('sabga_config', 'Check the league database configuration.', array('status' => 503));
        }
        $options = array(PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false, PDO::ATTR_TIMEOUT => 5);
        if (defined('SABGA_LEAGUES_DB_SSL_CA') && SABGA_LEAGUES_DB_SSL_CA !== '') {
            $options[PDO::MYSQL_ATTR_SSL_CA] = SABGA_LEAGUES_DB_SSL_CA;
            $options[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = true;
        }
        $stage = 'connection';
        try {
            $dsn = 'mysql:host=' . SABGA_LEAGUES_DB_HOST . ';port=' . $port .
                ';dbname=' . SABGA_LEAGUES_DB_NAME . ';charset=utf8mb4';
            $db = new PDO($dsn, SABGA_LEAGUES_DB_USER, SABGA_LEAGUES_DB_PASSWORD, $options);
            $stage = 'standings query';
            $statement = $db->prepare(self::standings_sql());
            $statement->execute(array($id, $id));
            $rows = $statement->fetchAll();
            $statement = null;
            $db = null;
            $payload = self::wrap($id, $rows, 'live');
            set_transient($key, $payload, self::CACHE_SECONDS);
            return $payload;
        } catch (Throwable $error) {
            self::$last_diagnostic = self::diagnostic($error, $stage);
            // Do not expose hostnames, SQL, credentials or driver exception messages.
            return new WP_Error('sabga_database', 'Unable to read league standings. Ask the site administrator to check the database connection and table permissions.', array('status' => 503));
        }
    }

    private static function wrap($id, $rows, $mode) {
        return array('mode' => $mode, 'group_id' => $id, 'group' => self::groups()[$id],
            'series' => '2026 · Series 4', 'fetched_at' => gmdate('c'),
            'cache_seconds' => self::CACHE_SECONDS, 'standings' => self::normalize($rows));
    }

    public static function routes() {
        register_rest_route('sabga-leagues/v1', '/standings', array(
            'methods' => 'GET', 'callback' => array(__CLASS__, 'rest_standings'),
            'permission_callback' => '__return_true',
            'args' => array('group' => array('default' => 91,
                'validate_callback' => function ($value) { return self::valid_group($value); },
                'sanitize_callback' => 'absint')),
        ));
    }

    public static function rest_standings($request) {
        $data = self::payload($request->get_param('group'));
        if (is_wp_error($data)) { return $data; }
        $response = new WP_REST_Response($data);
        $response->header('Cache-Control', 'no-store, max-age=0');
        return $response;
    }

    public static function columns() {
        return array('position' => '#', 'player' => 'Player', 'played' => 'Played',
            'points' => 'Points', 'points_percentage' => 'Points %', 'wins' => 'Wins',
            'pr_wins' => 'PR wins', 'h2h' => 'H2H', 'average_pr' => 'Avg PR',
            'losses' => 'Losses', 'win_percentage' => 'Win %', 'average_luck' => 'Avg luck');
    }

    public static function page_assets() {
        global $post;
        if ($post && has_shortcode($post->post_content, 'sabga_leagues')) {
            wp_enqueue_style('sabga-leagues', plugins_url('assets/standings.css', self::$plugin_file), array(), self::VERSION);
        }
    }

    public static function cell($key, $row) {
        if ($key === 'player') {
            return $row['name'] . ($row['nickname'] !== '' ? ' (' . $row['nickname'] . ')' : '');
        }
        if ($row[$key] === null) { return '—'; }
        if (in_array($key, array('points_percentage', 'win_percentage', 'average_pr', 'average_luck'), true)) {
            return number_format($row[$key], 2, '.', '') .
                (in_array($key, array('points_percentage', 'win_percentage'), true) ? '%' : '');
        }
        return (string) $row[$key];
    }

    public static function shortcode($attributes = array()) {
        $attributes = shortcode_atts(array('group' => '91'), $attributes, 'sabga_leagues');
        $id = $attributes['group'];
        if (!self::valid_group($id)) { return '<p>Choose a valid league group (91–101).</p>'; }
        // Also supports shareable links and a usable no-JavaScript fallback.
        if (isset($_GET['sabga_group']) && self::valid_group($_GET['sabga_group'])) {
            $id = (int) $_GET['sabga_group'];
        }
        $id = (int) $id;
        $data = self::payload($id);
        wp_enqueue_style('sabga-leagues', plugins_url('assets/standings.css', self::$plugin_file), array(), self::VERSION);
        wp_enqueue_script('sabga-leagues', plugins_url('assets/standings.js', self::$plugin_file), array(), self::VERSION, true);
        $uid = wp_unique_id('sabga-leagues-');
        ob_start();
        // Page builders can invoke the shortcode after wp_head without putting
        // it in post_content. Print any still-pending stylesheet in that case.
        if (did_action('wp_head') && !wp_style_is('sabga-leagues', 'done')) {
            wp_print_styles('sabga-leagues');
        }
        ?>
        <section class="sabga-leagues" data-endpoint="<?php echo esc_url(rest_url('sabga-leagues/v1/standings')); ?>" aria-label="SABGA league standings">
            <header class="sabga-leagues__header">
                <p class="sabga-leagues__eyebrow">SABGA ROUND ROBIN LEAGUES</p>
                <h2>League standings</h2>
                <p class="sabga-leagues__series">2026 · Series 4</p>
            </header>
            <div class="sabga-leagues__demo" <?php echo self::mode() === 'demo' ? '' : 'hidden'; ?>>Demo · Fictional players and results. This is a display test.</div>
            <form class="sabga-leagues__controls" method="get">
                <?php if (!get_option('permalink_structure') && get_queried_object_id()) : ?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?>
                <label for="<?php echo esc_attr($uid); ?>">League group</label>
                <select id="<?php echo esc_attr($uid); ?>" name="sabga_group">
                    <?php foreach (self::groups() as $gid => $label) : ?>
                    <option value="<?php echo esc_attr($gid); ?>" <?php selected($id, $gid); ?>><?php echo esc_html($label); ?></option>
                    <?php endforeach; ?>
                </select>
                <button type="submit">Show standings</button>
            </form>
            <p class="sabga-leagues__status" role="status" aria-live="polite"></p>
            <p class="sabga-leagues__error" role="alert" <?php echo is_wp_error($data) ? '' : 'hidden'; ?>><?php echo is_wp_error($data) ? esc_html($data->get_error_message()) : ''; ?></p>
            <h3 class="sabga-leagues__group"><?php echo esc_html(self::groups()[$id]); ?></h3>
            <div class="sabga-leagues__scroll" tabindex="0" role="region" aria-label="Standings table; scroll horizontally for more columns">
                <table>
                    <caption class="sabga-leagues__sr-only">Standings for <?php echo esc_html(self::groups()[$id]); ?></caption>
                    <thead><tr><?php foreach (self::columns() as $key => $label) : ?><th scope="col" data-key="<?php echo esc_attr($key); ?>"><?php echo esc_html($label); ?></th><?php endforeach; ?></tr></thead>
                    <tbody><?php if (!is_wp_error($data)) : foreach ($data['standings'] as $row) : ?><tr><?php foreach (self::columns() as $key => $label) : ?>
                        <?php if ($key === 'player') : ?><th scope="row"><?php echo esc_html(self::cell($key, $row)); ?></th>
                        <?php else : ?><td><?php echo esc_html(self::cell($key, $row)); ?></td><?php endif; ?>
                    <?php endforeach; ?></tr><?php endforeach; endif; ?></tbody>
                </table>
            </div>
            <p class="sabga-leagues__empty" <?php echo !is_wp_error($data) && !$data['standings'] ? '' : 'hidden'; ?>>No players with fixtures were found for this group.</p>
            <p class="sabga-leagues__warning" <?php echo !is_wp_error($data) && in_array(false, array_column($data['standings'], 'stats_available'), true) ? '' : 'hidden'; ?>>Some players have no precomputed statistics yet. Their standings show zero until the existing statistics process runs.</p>
            <p class="sabga-leagues__timestamp"><?php echo !is_wp_error($data) ? esc_html('Standings fetched ' . $data['fetched_at']) : ''; ?></p>
            <p class="sabga-leagues__note">Order: points, wins, PR wins, head-to-head score, average PR, then matches played. Points % = points ÷ (matches played × 3). Fetch time records when the website read the data; it is not the statistics calculation time.</p>
        </section>
        <?php return ob_get_clean();
    }

    public static function admin_menu() {
        add_options_page('SABGA Leagues', 'SABGA Leagues', 'manage_options', 'sabga-leagues', array(__CLASS__, 'admin_page'));
    }

    public static function admin_page() {
        if (!current_user_can('manage_options')) { return; }
        $notice = get_transient('sabga_lg_notice_' . get_current_user_id());
        delete_transient('sabga_lg_notice_' . get_current_user_id());
        ?>
        <div class="wrap"><h1>SABGA League Standings · Proof of concept</h1>
        <?php if (is_array($notice)) : ?><div class="notice notice-<?php echo esc_attr($notice['type']); ?>"><p><?php echo esc_html($notice['message']); ?></p></div><?php endif; ?>
        <p>Current series: 2026 Series 4. Shortcode: <code>[sabga_leagues]</code> or <code>[sabga_leagues group="92"]</code>.</p>
        <p>Database credentials: <strong><?php echo self::configured() ? 'Configured in wp-config.php' : 'Not configured'; ?></strong>. PHP PDO MySQL: <strong><?php echo class_exists('PDO') && in_array('mysql', PDO::getAvailableDrivers(), true) ? 'Available' : 'Missing'; ?></strong>.</p>
        <p>Credentials are read from server constants, never stored in this settings form. The league connection performs SELECT queries only. Cache duration: 60 seconds.</p>
        <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
            <input type="hidden" name="action" value="sabga_leagues_action">
            <?php wp_nonce_field('sabga_leagues_action'); ?>
            <label for="sabga-mode">Display mode</label>
            <select id="sabga-mode" name="mode"><option value="demo" <?php selected(self::mode(), 'demo'); ?>>Demo — fictional data</option><option value="live" <?php selected(self::mode(), 'live'); ?>>Live — league SQL database</option></select>
            <p><button class="button button-primary" name="operation" value="save">Save mode</button></p>
            <p><button class="button" name="operation" value="test">Test live A-League connection</button> <button class="button" name="operation" value="clear">Clear standings cache</button></p>
        </form>
        <p>Test live connection requires live mode to be saved first. It bypasses the cache and reads A-League using the same query as the public display. It does not modify the league database.</p>
        <p>Start on a private WordPress test page. Before public use, compare every standings column with Streamlit and check that new results reach the precomputed statistics tables.</p>
        </div>
        <?php
    }

    public static function admin_action() {
        if (!current_user_can('manage_options')) { wp_die('You do not have permission to change these settings.'); }
        check_admin_referer('sabga_leagues_action');
        $operation = isset($_POST['operation']) && is_string($_POST['operation']) ? sanitize_key($_POST['operation']) : '';
        $type = 'success';
        $message = 'Standings cache cleared.';
        if ($operation === 'save') {
            $mode = isset($_POST['mode']) && $_POST['mode'] === 'live' ? 'live' : 'demo';
            if ($mode === 'live' && !self::configured()) {
                $type = 'error'; $message = 'Add the database constants to wp-config.php before enabling live mode.';
            } else {
                update_option('sabga_leagues_mode', $mode);
                $message = 'Display mode saved: ' . $mode . '.';
            }
        } elseif ($operation === 'test') {
            if (self::mode() !== 'live') {
                $type = 'error'; $message = 'Save live mode first, then test the database connection.';
            } else {
                $start = microtime(true);
                $data = self::payload(91, true);
                if (is_wp_error($data)) {
                    $type = 'error'; $message = $data->get_error_message();
                    if (self::$last_diagnostic !== '') { $message .= ' ' . self::$last_diagnostic; }
                }
                else { $message = 'Live SELECT succeeded: ' . count($data['standings']) . ' A-League players in ' . round((microtime(true) - $start) * 1000) . ' ms. Compare these results with Streamlit.'; }
            }
        } elseif ($operation !== 'clear') {
            $type = 'error'; $message = 'Unknown action.';
        }
        if ($operation === 'save' || $operation === 'clear') {
            foreach (array_keys(self::groups()) as $id) { delete_transient(self::cache_key($id)); }
        }
        set_transient('sabga_lg_notice_' . get_current_user_id(), array('type' => $type, 'message' => $message), 60);
        wp_safe_redirect(admin_url('options-general.php?page=sabga-leagues'));
        exit;
    }
}
