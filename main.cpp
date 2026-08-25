#include <bits/stdc++.h>

using namespace std;

typedef long long ll;
typedef long double ld;
typedef pair<int, int> PII;
typedef pair<ll, ll> PLL;
typedef vector<int> VI;
typedef vector<ll> VL;
#define PB push_back
#define POP pop_back
#define MP make_pair
#define all(a) (a).begin(), (a).end()
#define SZ(a) (int)a.size()
#define endl '\n'
#define dbg(x) cerr << '[' << #x << ": " << x << "]\n"
#define dbg2(x, y) cerr << '[' << #x << ": " << x << ", " << #y << ": " << y << "]\n"
#define YES cout << "YES\n"
#define NO cout << "NO\n"

const ll INF = (ll)2e18 + 1386;
const ld eps = 0.000000000000001;
const int MOD = 1e9 + 7;

inline int _add(int a, int b){ int res = a + b; return (res >= MOD ? res - MOD : res); }
inline int _neg(int a, int b){ int res = (abs(a - b) < MOD ? a - b : (a - b) % MOD); return (res < 0 ? res + MOD : res); }
inline int _mlt(ll a, ll b){ return (a * b % MOD); }

const int MAXN = 5e5 + 5;

// xy XY

// gy gray
// gr green

int N, n;
int cap[MAXN];
vector<vector<string>> v; // 0 : bottom
bool gg[MAXN], mark[MAXN];
map<vector<vector<string>>, int> mp;
map<int, vector<vector<string>>> mp2;
map<string, int> colcnt;
pair<int, PII> par[MAXN];
int ID = 1;

void game_print(){
    cout << endl;
    for (int i = 0; i < 4; i++){
        for (int j = 1; j <= n; j++){
            if (SZ(v[j]) < 4 - i) cout << "00";
            else cout << v[j][4 - i - 1];
            cout << "  ";
        }
        cout << endl;
    }
    for (int i = 1; i <= n; i++){
        cout << i;
        if (i < 10) cout << ' ';
        cout << "  ";
    }
    cout << endl << endl;
}

void game_opr(int a, int b){
    string col = v[a].back();
    v[a].POP();
    v[b].PB(col);
}

pair<string, int> get_data(int a){
    if (v[a].empty()) return MP("00", 0);
    string x = v[a].back();
    int res = 0;
    for (int j = SZ(v[a]) - 1; j >= 0; j--){
        if (v[a][j] == x) res++;
        else break;
    }
    return MP(x, res);
}

bool check_valid(int a, int b){
    if (a == b) return 0;
    if (min(a, b) < 0 || max(a, b) > n) return 0;
    if (v[a].empty()) return 0;
    if (v[b].empty()) return 1;
    pair<string, int> p1 = get_data(a);
    pair<string, int> p2 = get_data(b);
    if (p1.first != p2.first) return 0;
    if (p1.second + SZ(v[b]) > cap[b]) return 0;
    return 1;
}

bool check_optimize(int a, int b){
    if (get_data(a).second == SZ(v[a]) && v[b].empty()) return 0;
    return 1;
}

void check_endstate(){
    int x = 0;
    set<string> all_colors;
    for (int i = 1; i <= n; i++){
        gg[i] = 0;
        //if (get_data(i).second == 4 || get_data(i).second == 0) gg[i] = 1;
        x += gg[i];
        if (v[i].empty()) continue;
        for (auto x : v[i]) all_colors.insert(x);
        if (v[i].back() == "? ") gg[0] = 1;
    }
    //dbg("BEGIN");
    for (auto c : all_colors){
        //dbg(c);
        bool flag = 0;
        for (int i = 1; i <= n; i++){
            set<string> bottlecolor;
            for (auto curcol : v[i]){
                if (curcol != "? "){
                    bottlecolor.insert(curcol);
                    if (SZ(bottlecolor) > 1) return;
                }
            }
            for (auto curcol : bottlecolor){
                if (curcol == c){
                    if (flag) return;
                    flag = 1;
                }
            }
        }
    }
    //dbg("END");
    gg[0] = 1;
    //if (x == n) gg[0] = 1;
}

void dfs(int curid){
    //dbg(curid);
    mark[curid] = 1;
    auto curvec = mp2[curid];
    check_endstate();
    if (gg[0]) return;
    for (int i = 1; i <= n; i++){
        for (int j = 1; j <= n; j++){
            v = curvec;
            if (!check_valid(i, j)) continue;
            if (!check_optimize(i, j)) continue;
            int val = get_data(i).second;
            while (val--) game_opr(i, j);
            auto nextvec = v;
            if (mp.find(nextvec) != mp.end()) continue;
            int nextid = ID++;
            mp[nextvec] = nextid;
            mp2[nextid] = nextvec;
            par[nextid] = MP(curid, MP(i, j));
            dfs(nextid);
            if (gg[0]) return;
        }
    }
}

int main(){
    //ios_base::sync_with_stdio(0); cin.tie(0);
    cin >> n;
    N = n;
    bool flag = 0;
    vector<string> tmp;
    int mxcap = 0;
    for (int i = 0; i <= n; i++) v.PB(tmp);
    for (int i = 1; i <= n; i++){
        cin >> cap[i];
        mxcap = max(mxcap, cap[i]);
        int k;
        cin >> k;
        //cout << "Bottle #";
        //if (i < 10) cout << '0';
        //cout << i << " : ";
        for (int j = 0; j < k; j++){
            string inp;
            if (!flag) cin >> inp;
            if (inp == "0") flag = 1;
            if (flag) continue;
            if (inp == "?") inp = "? ";
            colcnt[inp]++;
            v[i].PB(inp);
        }
    }
    for (auto [col, cnt] : colcnt){
        if (col != "? " && cnt > mxcap) return cout << "CANT BE SOLVED\n", 0;
    }
    check_endstate();
    //game_print();
    mp[v] = ID;
    mp2[ID++] = v;
    dfs(1);
    //dbg(gg[0]);
    if (!gg[0]) return cout << "CANT BE SOLVED\n", 0;
    cout << "DONE\n";
    v = mp2[ID - 1];
    //game_print();
    vector<PII> oprs;
    int cur = ID - 1;
    while (cur != 1){
        oprs.PB(par[cur].second);
        cur = par[cur].first;
    }
    //dbg(SZ(oprs));
    cout << SZ(oprs) << endl;
    while (!oprs.empty()){
        auto [a, b] = oprs.back();
        cout << a << ' ' << b << endl;
        oprs.POP();
    }
    /*while (16 == 16){
        if (gg[0]) break;
        game_print();
        //int a, b, val;
        //cin >> a >> b >> val;
        //while (val--) game_opr(a, b);
        int a, b;
        cin >> a >> b;
        if (!check_valid(a, b)){
            cout << "NOT A VALID MOVE\n" << endl;
            continue;
        }
        int val = get_data(a).second;
        while (val--) game_opr(a, b);
        upd_gg();
    }
    cout << "WELL DONE!\n";
    cout << "You finished the game in " << SZ(oprs) << " move(s)\n";
    cout << "Here is the list of operations:\n";
    for (auto [a, b] : oprs) cout << a << ' ' << b << endl;*/
    return 0;
}

