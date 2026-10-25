package com.treasure.game;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.webkit.WebViewAssetLoader;

import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;

/** 用 WebView 承载《解密·四界征战》网页版，assets/www 里是打包好的游戏。 */
public class MainActivity extends Activity {

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        web = new WebView(this);
        web.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));
        web.setPadding(0, 0, 0, 0);
        web.setVerticalScrollBarEnabled(false);
        web.setHorizontalScrollBarEnabled(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // localStorage 存档
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        s.setSupportZoom(false);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setTextZoom(100);
        web.setInitialScale(100);

        // 用 https://appassets.androidplatform.net 提供本地文件，避免 file:// 的 fetch 限制
        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.PathHandler() {
                    @Override
                    public WebResourceResponse handle(String path) {
                        try {
                            InputStream is = getAssets().open(path);
                            String mime = mimeOf(path);
                            Map<String, String> headers = new HashMap<>();
                            headers.put("Cache-Control", "no-store, no-cache, must-revalidate");
                            return new WebResourceResponse(mime, "utf-8", 200, "OK", headers, is);
                        } catch (IOException e) {
                            return null;
                        }
                    }
                })
                .build();

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return loader.shouldInterceptRequest(request.getUrl());
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request,
                                        WebResourceError error) {
                // 主页面加载失败时给出可读提示，避免黑屏无反馈
                if (request.isForMainFrame()) {
                    view.loadDataWithBaseURL(null,
                            "<html><body style='background:#140F1C;color:#FFD9EC;"
                                    + "font-family:sans-serif;display:flex;align-items:center;"
                                    + "justify-content:center;height:100vh;margin:0;text-align:center'>"
                                    + "<div><h2>游戏启动失败</h2>"
                                    + "<p>请确认安装包完整，或退出后重新打开。<br>"
                                    + "如果是覆盖安装失败，请先卸载旧版再重装。</p></div></body></html>",
                            "text/html", "utf-8", null);
                }
            }
        });
        web.setWebChromeClient(new WebChromeClient());
        web.setBackgroundColor(0xFF140F1C);
        setContentView(web);

        hideSystemUi();
        web.loadUrl("https://appassets.androidplatform.net/assets/www/index.html");
    }

    /** 给 wasm / data 等资源正确的 MIME，避免 WebAssembly 流式加载失败。 */
    private static String mimeOf(String path) {
        String p = path.toLowerCase();
        if (p.endsWith(".wasm")) return "application/wasm";
        if (p.endsWith(".js") || p.endsWith(".mjs")) return "text/javascript";
        if (p.endsWith(".html") || p.endsWith(".htm")) return "text/html";
        if (p.endsWith(".css")) return "text/css";
        if (p.endsWith(".json")) return "application/json";
        if (p.endsWith(".png")) return "image/png";
        if (p.endsWith(".ttf")) return "font/ttf";
        return "application/octet-stream";
    }

    private void hideSystemUi() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        |
                View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemUi();
    }

    @Override
    public void onBackPressed() {
        // 游戏里没有可回退的页面，直接退出
        finish();
    }
}
