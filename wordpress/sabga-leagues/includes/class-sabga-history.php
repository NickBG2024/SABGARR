<?php
if (!defined('ABSPATH')) { exit; }

final class SABGA_History {
    private static $file;
    const CURRENT_SERIES = 13; // Same current-series baseline as SABGARRLive.py.

    public static function boot($file) {
        self::$file = $file;
        add_shortcode('sabga_history', array(__CLASS__, 'shortcode'));
        add_action('rest_api_init', array(__CLASS__, 'routes'));
        add_action('wp_enqueue_scripts', function () {
            global $post;
            if ($post && has_shortcode($post->post_content, 'sabga_history')) {
                wp_enqueue_style('sabga-history', plugins_url('assets/history.css', self::$file), array(), SABGA_Leagues::VERSION);
            }
        });
    }

    public static function tabs() {
        return array('standings'=>'Previous standings', 'annual'=>'Player of the Year',
            'pr'=>'League PR trends', 'players'=>'Player records');
    }

    private static function connection() {
        if (!SABGA_Leagues::configured()) { throw new RuntimeException('Configuration unavailable'); }
        $port = defined('SABGA_LEAGUES_DB_PORT') ? (int) SABGA_LEAGUES_DB_PORT : 3306;
        if ($port < 1 || $port > 65535 || preg_match('/[;\x00-\x1f]/', SABGA_LEAGUES_DB_HOST . SABGA_LEAGUES_DB_NAME)) {
            throw new RuntimeException('Invalid configuration');
        }
        $options = array(PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES=>false, PDO::ATTR_TIMEOUT=>5);
        if (defined('SABGA_LEAGUES_DB_SSL_CA') && SABGA_LEAGUES_DB_SSL_CA !== '') {
            $options[PDO::MYSQL_ATTR_SSL_CA] = SABGA_LEAGUES_DB_SSL_CA;
            $options[PDO::MYSQL_ATTR_SSL_VERIFY_SERVER_CERT] = true;
        }
        return new PDO('mysql:host=' . SABGA_LEAGUES_DB_HOST . ';port=' . $port . ';dbname=' . SABGA_LEAGUES_DB_NAME . ';charset=utf8mb4',
            SABGA_LEAGUES_DB_USER, SABGA_LEAGUES_DB_PASSWORD, $options);
    }

    public static function catalog_sql() {
        return 'SELECT DISTINCT ss.SeasonID AS season_id, s.SeriesID AS series_id, s.SeriesTitle AS series,
            mt.MatchTypeID AS group_id, mt.MatchTypeTitle AS league
            FROM SeasonSeries ss JOIN Series s ON s.SeriesID = ss.SeriesID
            JOIN SeriesMatchTypes sm ON sm.SeriesID = s.SeriesID
            JOIN MatchType mt ON mt.MatchTypeID = sm.MatchTypeID
            ORDER BY ss.SeasonID DESC, s.SeriesID DESC, mt.MatchTypeID';
    }

    private static function demo_catalog() {
        $rows = array();
        foreach (array(1=>array(5=>'2025 - Series 1',8=>'2025 - Series 4'),2=>array(10=>'2026 - Series 1',12=>'2026 - Series 3',13=>'2026 - Series 4')) as $season=>$series) {
            foreach ($series as $sid=>$title) {
                foreach (array(1=>'A-League',2=>'B-League') as $n=>$league) {
                    $rows[] = array('season_id'=>$season,'series_id'=>$sid,'series'=>$title,'group_id'=>$sid*10+$n,'league'=>$league);
                }
            }
        }
        return $rows;
    }

    public static function catalog() {
        if (SABGA_Leagues::mode() === 'demo') { return self::demo_catalog(); }
        $key = SABGA_Leagues::cache_key(0) . '_catalog';
        $cache = get_transient($key);
        if (is_array($cache)) { return $cache; }
        try {
            $rows = self::connection()->query(self::catalog_sql())->fetchAll();
            foreach ($rows as &$row) {
                foreach (array('season_id','series_id','group_id') as $key_name) { $row[$key_name] = (int) $row[$key_name]; }
            }
            unset($row);
            set_transient($key, $rows, 60);
            return $rows;
        } catch (Throwable $error) {
            return new WP_Error('sabga_history_catalog', 'Historical records could not be loaded. Ask the site administrator to check the archive tables and read permissions.', array('status'=>503));
        }
    }

    public static function season_label($id) {
        // IDs from the existing Streamlit season_mapping, not inferred from sequence.
        return array(1=>'2025',2=>'2026')[$id] ?? 'Season ' . (int) $id;
    }

    public static function integer($value) {
        return is_scalar($value) && preg_match('/^[1-9][0-9]{0,9}$/D', (string) $value) ? (int) $value : 0;
    }

    public static function select($catalog, $input) {
        $tab = isset($input['tab']) && is_string($input['tab']) ? $input['tab'] : 'standings';
        if (!isset(self::tabs()[$tab])) { return new WP_Error('sabga_history_selection','Choose a valid records tab.',array('status'=>400)); }
        $seasons = array_values(array_unique(array_column($catalog,'season_id')));
        rsort($seasons, SORT_NUMERIC);
        $season = isset($input['season']) ? self::integer($input['season']) : ($seasons[0] ?? 0);
        if (!in_array($season,$seasons,true)) { return new WP_Error('sabga_history_selection','Choose an available season.',array('status'=>400)); }
        $season_rows = array_values(array_filter($catalog,function($r) use($season){return $r['season_id']===$season;}));
        $series_ids = array_values(array_unique(array_column(array_filter($season_rows,function($r){return $r['series_id']!==self::CURRENT_SERIES;}),'series_id')));
        rsort($series_ids,SORT_NUMERIC);
        $series = isset($input['series']) ? self::integer($input['series']) : ($series_ids[0] ?? 0);
        if ($tab==='standings' && $series_ids && !in_array($series,$series_ids,true)) {
            return new WP_Error('sabga_history_selection','Choose a previous series in this season.',array('status'=>400));
        }
        $groups = array_values(array_filter($season_rows,function($r)use($series){return $r['series_id']===$series;}));
        $group = isset($input['group']) ? self::integer($input['group']) : ($groups[0]['group_id'] ?? 0);
        if ($tab==='standings' && $series_ids && !in_array($group,array_column($groups,'group_id'),true)) {
            return new WP_Error('sabga_history_selection','Choose a group belonging to this series.',array('status'=>400));
        }
        if (isset($input['player']) && !self::integer($input['player'])) { return new WP_Error('sabga_history_selection','Choose a valid player.',array('status'=>400)); }
        return array('tab'=>$tab,'season'=>$season,'series'=>$series,'group'=>$group,
            'player'=>isset($input['player']) ? self::integer($input['player']) : 0,
            'has_previous'=>(bool)$series_ids,'season_rows'=>$season_rows,'groups'=>$groups);
    }

    public static function player_pr_sql() {
        // One row per player's recorded PR per match, as get_player_pr_for_season.
        return 'SELECT p.PlayerID AS player_id, p.Name AS name, p.Nickname AS nickname,
            sm.SeriesID AS series_id, s.SeriesTitle AS series, COUNT(*) AS matches, AVG(pr.player_pr) AS average_pr
            FROM (SELECT MatchTypeID, Player1ID AS player_id, Player1PR AS player_pr FROM MatchResults WHERE Player1PR IS NOT NULL
                UNION ALL SELECT MatchTypeID, Player2ID AS player_id, Player2PR AS player_pr FROM MatchResults WHERE Player2PR IS NOT NULL) pr
            JOIN Players p ON p.PlayerID=pr.player_id
            JOIN (SELECT DISTINCT SeriesID, MatchTypeID FROM SeriesMatchTypes) sm ON sm.MatchTypeID=pr.MatchTypeID
            JOIN Series s ON s.SeriesID=sm.SeriesID
            WHERE EXISTS (SELECT 1 FROM SeasonSeries ss WHERE ss.SeriesID=sm.SeriesID AND ss.SeasonID=?)
            GROUP BY p.PlayerID,p.Name,p.Nickname,sm.SeriesID,s.SeriesTitle ORDER BY sm.SeriesID,p.Name';
    }

    public static function pr_sql() {
        return 'SELECT sm.SeriesID AS series_id,s.SeriesTitle AS series,mt.MatchTypeTitle AS league,
            AVG((mr.Player1PR + mr.Player2PR) / 2) AS average_pr
            FROM MatchResults mr JOIN Fixtures f ON mr.FixtureID=f.FixtureID AND mr.MatchTypeID=f.MatchTypeID
            JOIN MatchType mt ON mt.MatchTypeID=f.MatchTypeID
            JOIN (SELECT DISTINCT SeriesID,MatchTypeID FROM SeriesMatchTypes) sm ON sm.MatchTypeID=f.MatchTypeID
            JOIN Series s ON s.SeriesID=sm.SeriesID
            WHERE mr.Player1PR IS NOT NULL AND mr.Player2PR IS NOT NULL
            AND EXISTS(SELECT 1 FROM SeasonSeries ss WHERE ss.SeriesID=sm.SeriesID AND ss.SeasonID=?)
            GROUP BY sm.SeriesID,s.SeriesTitle,mt.MatchTypeTitle ORDER BY sm.SeriesID,mt.MatchTypeTitle';
    }

    public static function player_sql() {
        return 'SELECT sm.SeriesID AS series_id,s.SeriesTitle AS series,mt.MatchTypeTitle AS league,
            COUNT(*) AS played,SUM(CASE WHEN r.own_points>r.other_points THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN r.own_points<r.other_points THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN r.own_pr<r.other_pr THEN 1 ELSE 0 END) AS pr_wins,AVG(r.own_pr) AS average_pr
            FROM (SELECT MatchTypeID,Player1ID AS player_id,Player1Points AS own_points,Player2Points AS other_points,Player1PR AS own_pr,Player2PR AS other_pr FROM MatchResults
                UNION ALL SELECT MatchTypeID,Player2ID AS player_id,Player2Points AS own_points,Player1Points AS other_points,Player2PR AS own_pr,Player1PR AS other_pr FROM MatchResults) r
            JOIN (SELECT DISTINCT SeriesID,MatchTypeID FROM SeriesMatchTypes) sm ON sm.MatchTypeID=r.MatchTypeID
            JOIN Series s ON s.SeriesID=sm.SeriesID JOIN MatchType mt ON mt.MatchTypeID=r.MatchTypeID
            WHERE r.player_id=? AND EXISTS(SELECT 1 FROM SeasonSeries ss WHERE ss.SeriesID=sm.SeriesID AND ss.SeasonID=?)
            GROUP BY sm.SeriesID,s.SeriesTitle,mt.MatchTypeTitle ORDER BY sm.SeriesID';
    }

    public static function annual_table($rows, $series) {
        $people = array();
        foreach ($rows as $r) {
            $id=(int)$r['player_id'];
            if (!isset($people[$id])) { $people[$id]=array('name'=>self::name($r),'matches'=>0,'sum'=>0,'series'=>array()); }
            $n=(int)$r['matches']; $people[$id]['matches']+=$n; $people[$id]['sum']+=(float)$r['average_pr']*$n;
            $people[$id]['series'][(int)$r['series_id']]=(float)$r['average_pr'];
        }
        foreach ($people as &$p) { $p['pr']=$p['matches'] ? round($p['sum']/$p['matches'],2) : null; } unset($p);
        uasort($people,function($a,$b){return ($a['pr'] <=> $b['pr']) ?: strcmp($a['name'],$b['name']);});
        $result=array();
        foreach ($people as $p) {
            $line=array($p['name'],$p['matches'],self::decimal($p['pr']));
            foreach ($series as $sid=>$title) { $line[]=self::decimal($p['series'][$sid] ?? null); }
            $result[]=$line;
        }
        return $result;
    }

    public static function name($r) { return $r['name'] . (!empty($r['nickname']) ? ' (' . $r['nickname'] . ')' : ''); }
    public static function decimal($v) { return $v===null ? '—' : number_format((float)$v,2,'.',''); }

    private static function demo($selection) {
        $tab=$selection['tab'];
        if ($tab==='standings') { $data=SABGA_Leagues::payload(91); $rows=array(); foreach($data['standings'] as $r){$rows[]=array($r['position'],self::name($r),$r['played'],$r['points'],self::decimal($r['points_percentage']).'%',$r['wins'],$r['pr_wins'],$r['h2h'],self::decimal($r['average_pr']),$r['losses'],self::decimal($r['win_percentage']).'%',self::decimal($r['average_luck']));} return array('columns'=>array_values(SABGA_Leagues::columns()),'rows'=>$rows,'note'=>'Fictional historical standings.'); }
        if($tab==='annual') { return array('columns'=>array('Player','PR matches','Average PR','Series 1','Series 4'),'rows'=>array(array('Demo Player One',16,'6.12','6.34','5.90'),array('Demo Player Two',12,'7.42','7.11','7.73')),'note'=>'Fictional PR standings. This is not an awards register.'); }
        if($tab==='pr') { return array('columns'=>array('League','Series 1','Series 4'),'rows'=>array(array('A-League','6.70','6.30'),array('B-League','9.38','8.48')),'note'=>'Fictional group averages. Lower PR indicates stronger play.'); }
        return array('columns'=>array('Series','League','Played','Wins','Losses','PR wins','Avg PR'),'rows'=>array(array('Demo Series 1','A-League',8,5,3,4,'6.34'),array('Demo Series 4','B-League',8,6,2,5,'5.90')),'note'=>'Fictional selected-season player records.');
    }

    public static function report($input) {
        $catalog=self::catalog(); if(is_wp_error($catalog)){return $catalog;}
        $sel=self::select($catalog,$input); if(is_wp_error($sel)){return $sel;}
        if(SABGA_Leagues::mode()==='demo'){return self::demo($sel);}
        $key=SABGA_Leagues::cache_key(0).'_history_'.md5(serialize(array($sel['tab'],$sel['season'],$sel['series'],$sel['group'],$sel['player'])));
        $cache=get_transient($key); if(is_array($cache)){return $cache;}
        try {
            $db=self::connection(); $series=array();
            foreach($sel['season_rows'] as $r){$series[$r['series_id']]=$r['series'];} ksort($series,SORT_NUMERIC);
            if($sel['tab']==='standings'){
                if(!$sel['has_previous']){return array('columns'=>array('Player'),'rows'=>array(),'note'=>'No previous series is linked to this season yet.');}
                $st=$db->prepare(SABGA_Leagues::standings_sql()); $st->execute(array($sel['group'],$sel['group']));
                $rows=array(); foreach(SABGA_Leagues::normalize($st->fetchAll()) as $r){$line=array();foreach(array_keys(SABGA_Leagues::columns()) as $k){$line[]=SABGA_Leagues::cell($k,$r);} $rows[]=$line;}
                $data=array('columns'=>array_values(SABGA_Leagues::columns()),'rows'=>$rows,'note'=>'Recorded standings for the selected previous series. Ordering matches the current league display.');
            } elseif($sel['tab']==='annual'){
                $st=$db->prepare(self::player_pr_sql());$st->execute(array($sel['season']));
                $data=array('columns'=>array_merge(array('Player','PR matches','Average PR'),array_values($series)),
                    'rows'=>self::annual_table($st->fetchAll(),$series),'note'=>'PR standings using the Streamlit calculation: average of each player’s recorded match PR, lowest first. No minimum-match eligibility rule is applied. This is not a confirmed awards register.');
            } elseif($sel['tab']==='pr'){
                $st=$db->prepare(self::pr_sql());$st->execute(array($sel['season'])); $leagues=array();
                foreach($st->fetchAll() as $r){$leagues[$r['league']][(int)$r['series_id']]=(float)$r['average_pr'];} ksort($leagues,SORT_NATURAL);
                $rows=array();foreach($leagues as $league=>$values){$line=array($league);foreach($series as $sid=>$title){$line[]=self::decimal($values[$sid] ?? null);} $rows[]=$line;}
                $data=array('columns'=>array_merge(array('League'),array_values($series)),'rows'=>$rows,'note'=>'Average match PR for each league and series. Only matches with both player PRs recorded contribute, matching Streamlit.');
            } else {
                $players=self::players($sel['season']);if(is_wp_error($players)){return $players;}
                $pid=$sel['player'] ?: ($players[0]['id'] ?? 0);
                if($pid && !in_array($pid,array_column($players,'id'),true)){return new WP_Error('sabga_history_selection','Choose a player with results in this season.',array('status'=>400));}
                $st=$db->prepare(self::player_sql());$st->execute(array($pid,$sel['season']));$rows=array();
                foreach($st->fetchAll() as $r){$rows[]=array($r['series'],$r['league'],(int)$r['played'],(int)$r['wins'],(int)$r['losses'],(int)$r['pr_wins'],self::decimal($r['average_pr']));}
                $data=array('columns'=>array('Series','League','Played','Wins','Losses','PR wins','Avg PR'),'rows'=>$rows,'note'=>'Selected-season match records by series and historical group. A PR win requires a lower PR than the opponent; missing PRs do not count as PR wins.');
            }
            if(isset($series[self::CURRENT_SERIES]) && $sel['tab']!=='standings'){$data['note'].=' This season includes the current series and remains provisional.';}
            set_transient($key,$data,60);return $data;
        } catch(Throwable $error){return new WP_Error('sabga_history_database','This records tab could not be loaded. Ask the site administrator to check its archive tables and read permissions.',array('status'=>503));}
    }

    public static function players($season) {
        if(SABGA_Leagues::mode()==='demo'){return array(array('id'=>1,'label'=>'Demo Player One'),array('id'=>2,'label'=>'Demo Player Two'));}
        $key=SABGA_Leagues::cache_key(0).'_players_'.(int)$season; $cache=get_transient($key);if(is_array($cache)){return $cache;}
        try{
            $db=self::connection();$st=$db->prepare('SELECT DISTINCT p.PlayerID AS id,p.Name AS name,p.Nickname AS nickname FROM Players p
                JOIN MatchResults mr ON (mr.Player1ID=p.PlayerID OR mr.Player2ID=p.PlayerID)
                WHERE EXISTS(SELECT 1 FROM SeriesMatchTypes sm JOIN SeasonSeries ss ON ss.SeriesID=sm.SeriesID WHERE sm.MatchTypeID=mr.MatchTypeID AND ss.SeasonID=?) ORDER BY p.Name,p.PlayerID');
            $st->execute(array($season));$rows=array();foreach($st->fetchAll() as $r){$rows[]=array('id'=>(int)$r['id'],'label'=>self::name($r));}
            set_transient($key,$rows,60);return $rows;
        }catch(Throwable $error){return new WP_Error('sabga_history_players','The player list could not be loaded.',array('status'=>503));}
    }

    public static function routes(){
        register_rest_route('sabga-leagues/v1','/history',array('methods'=>'GET','permission_callback'=>'__return_true','callback'=>function($request){
            $input=array();foreach(array('tab','season','series','group','player') as $key){$v=$request->get_param($key);if($v!==null && $v!==''){$input[$key]=$v;}}
            $data=self::report($input);if(is_wp_error($data)){return $data;}$response=new WP_REST_Response($data);$response->header('Cache-Control','no-store, max-age=0');return $response;
        }));
    }

    public static function table($data){
        if(is_wp_error($data)){return '<p role="alert">'.esc_html($data->get_error_message()).'</p>';}
        $html='<p class="sabga-history__note">'.esc_html($data['note']).'</p><div class="sabga-history__scroll" tabindex="0" role="region" aria-label="Historical records table; scroll for more columns"><table><caption class="sabga-history__sr-only">Historical records</caption><thead><tr>';
        foreach($data['columns'] as $label){$html.='<th scope="col"'.(in_array($label,array('Player','League','Series'),true)?' class="sabga-history__text"':'').'>'.esc_html($label).'</th>';}$html.='</tr></thead><tbody>';
        foreach($data['rows'] as $row){$html.='<tr>';foreach($row as $i=>$value){$tag=$i===0?'th':'td';$html.='<'.$tag.($i===0?' scope="row"':'').(in_array($data['columns'][$i],array('Player','League','Series'),true)?' class="sabga-history__text"':'').'>'.esc_html($value).'</'.$tag.'>';}$html.='</tr>';}
        $html.='</tbody></table></div>';if(!$data['rows']){$html.='<p>No records found for this selection.</p>';}return $html;
    }

    public static function shortcode(){
        wp_enqueue_style('sabga-history',plugins_url('assets/history.css',self::$file),array(),SABGA_Leagues::VERSION);
        wp_enqueue_script('sabga-history',plugins_url('assets/history.js',self::$file),array(),SABGA_Leagues::VERSION,true);
        if(did_action('wp_head') && !wp_style_is('sabga-history','done')){wp_print_styles('sabga-history');}
        $catalog=self::catalog();if(is_wp_error($catalog)){return self::table($catalog);}
        $input=array();foreach(array('tab','season','series','group','player') as $key){if(isset($_GET['sabga_history_'.$key])){$input[$key]=$_GET['sabga_history_'.$key];}}
        // Season/series controls submit only applicable selectors, so dependencies cannot go stale.
        $sel=self::select($catalog,$input);if(is_wp_error($sel)){return self::table($sel);}
        $players=$sel['tab']==='players'?self::players($sel['season']):array();
        $seasons=array_values(array_unique(array_column($catalog,'season_id')));rsort($seasons,SORT_NUMERIC);
        $series=array();foreach($sel['season_rows'] as $r){if($r['series_id']!==self::CURRENT_SERIES){$series[$r['series_id']]=$r['series'];}}krsort($series,SORT_NUMERIC);
        $uid=wp_unique_id('sabga-history-');ob_start(); ?>
        <section class="sabga-history" data-selection="<?php echo esc_attr(json_encode(array('sabga_history_tab'=>$sel['tab'],'sabga_history_season'=>$sel['season']))); ?>" data-endpoint="<?php echo esc_url(rest_url('sabga-leagues/v1/history')); ?>" aria-label="SABGA historical records">
        <h2>Historical records</h2><p>Explore previous league standings, annual PR standings and player performance.</p>
        <?php if(SABGA_Leagues::mode()==='demo'):?><p class="sabga-history__demo">Demo · All records below are fictional.</p><?php endif; ?>
        <form method="get" class="sabga-history__season-form"><label for="<?php echo esc_attr($uid.'season'); ?>">Season</label>
        <?php if(!get_option('permalink_structure') && get_queried_object_id()):?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?>
        <input type="hidden" name="sabga_history_tab" value="<?php echo esc_attr($sel['tab']); ?>"><select id="<?php echo esc_attr($uid.'season'); ?>" name="sabga_history_season"><?php foreach($seasons as $sid):?><option value="<?php echo esc_attr($sid); ?>" <?php selected($sel['season'],$sid); ?>><?php echo esc_html(self::season_label($sid)); ?></option><?php endforeach; ?></select><button type="submit">Show season</button></form>
        <nav class="sabga-history__tabs" aria-label="Record sections"><?php foreach(self::tabs() as $key=>$label):
            $url=add_query_arg(array('sabga_history_tab'=>$key,'sabga_history_season'=>$sel['season'],'sabga_history_series'=>false,'sabga_history_group'=>false,'sabga_history_player'=>false)); ?>
            <a href="<?php echo esc_url($url); ?>" data-tab="<?php echo esc_attr($key); ?>" <?php echo $sel['tab']===$key?'aria-current="page"':''; ?>><?php echo esc_html($label); ?></a><?php endforeach; ?></nav>
        <h3><?php echo esc_html(self::tabs()[$sel['tab']]); ?></h3>
        <?php if($sel['tab']==='standings' && $sel['has_previous']): ?>
        <form method="get" class="sabga-history__series-form"><?php if(!get_option('permalink_structure') && get_queried_object_id()):?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?><input type="hidden" name="sabga_history_tab" value="standings"><input type="hidden" name="sabga_history_season" value="<?php echo esc_attr($sel['season']); ?>">
        <label for="<?php echo esc_attr($uid.'series'); ?>">Series</label><select id="<?php echo esc_attr($uid.'series'); ?>" name="sabga_history_series"><?php foreach($series as $sid=>$title):?><option value="<?php echo esc_attr($sid); ?>" <?php selected($sel['series'],$sid); ?>><?php echo esc_html($title); ?></option><?php endforeach; ?></select><button type="submit">Show series</button></form>
        <form method="get" class="sabga-history__report-form"><?php if(!get_option('permalink_structure') && get_queried_object_id()):?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?><input type="hidden" name="sabga_history_tab" value="standings"><input type="hidden" name="sabga_history_season" value="<?php echo esc_attr($sel['season']); ?>"><input type="hidden" name="sabga_history_series" value="<?php echo esc_attr($sel['series']); ?>">
        <label for="<?php echo esc_attr($uid.'group'); ?>">League group</label><select id="<?php echo esc_attr($uid.'group'); ?>" name="sabga_history_group"><?php foreach($sel['groups'] as $r):?><option value="<?php echo esc_attr($r['group_id']); ?>" <?php selected($sel['group'],$r['group_id']); ?>><?php echo esc_html($r['league']); ?></option><?php endforeach; ?></select><button type="submit">Show standings</button></form>
        <?php elseif($sel['tab']==='players' && !is_wp_error($players)):?>
        <form method="get" class="sabga-history__report-form"><?php if(!get_option('permalink_structure') && get_queried_object_id()):?><input type="hidden" name="page_id" value="<?php echo esc_attr(get_queried_object_id()); ?>"><?php endif; ?><input type="hidden" name="sabga_history_tab" value="players"><input type="hidden" name="sabga_history_season" value="<?php echo esc_attr($sel['season']); ?>">
        <label for="<?php echo esc_attr($uid.'player'); ?>">Player</label><select id="<?php echo esc_attr($uid.'player'); ?>" name="sabga_history_player"><?php foreach($players as $r):?><option value="<?php echo esc_attr($r['id']); ?>" <?php selected($sel['player'] ?: ($players[0]['id'] ?? 0),$r['id']); ?>><?php echo esc_html($r['label']); ?></option><?php endforeach; ?></select><button type="submit">Show player</button></form>
        <?php endif; ?>
        <p class="sabga-history__status" role="status" aria-live="polite"></p><div class="sabga-history__report"><?php echo self::table(self::report($input)); ?></div>
        </section><?php return ob_get_clean();
    }
}
