angular.module("Oscar", ["ngResource","ngSanitize","ui.bootstrap","ui.select2", "angularFileUpload"])
.controller("IndexController", ["$scope", "$resource", function($scope, $resource) {
    var info = $resource("./_info");
    $scope.info = info.get({}, function(result) {
        angular.forEach(result.shares, function(share) {
            share.info = $resource("./" + share.name + "/_info").get();
        }, function() {
            $scope.info = {error:true}
        });
    });
    $scope.alert_class = function(loadavg) {
        var classes = ["alert"];
        if (loadavg > 3.0) {
            classes.push("alert-danger");
        } else if (loadavg > 1.0) {
            classes.push("alert-warning");
        } else {
            classes.push("alert-success");
        }
        return classes;
    }
}])
.controller("ShareController", ["$scope", "$resource","$location","$timeout", function($scope, $resource,$location,$timeout) {
    var info = $resource("./_info");
    var dir = $resource("./_dir");
    var search = $resource("./_search");
    var filetypes = {
        ".ai":"ai", ".avi":"avi",
        ".bmp":"bmp",
        ".cab":"cab", ".css":"css",
        ".dll":"dll", ".doc":"doc", ".docx":"docx", ".dot":"dot", ".dwg":"dwg", ".dxf":"dxf",
        ".emf":"emf", ".eml":"eml", ".eps":"eps", ".exe":"exe",
        ".fla":"fla", ".fon":"fon",
        ".gif":"gif", ".gz":"gz",
        ".hqx":"hqx", ".htm":"html", ".html":"html",
        ".ico":"ico",
        ".jar":"jar", ".jpg":"jpg", ".js":"js", ".jtd":"jtd",
        ".log":"log", ".lzh":"lzh",
        ".m4a":"m4a", ".m4v":"m4v", ".mdb":"mdb", ".mid":"mid", ".mov":"mov", ".mp3":"mp3", ".mp4":"mp4", ".mpg":"mpg",
        ".ogg":"ogg",
        ".pdf":"pdf", ".php":"php", ".png":"png", ".ppt":"ppt", ".pptx":"pptx", ".ps":"ps", ".psd":"psd",
        ".rtf":"rtf",
        ".sit":"sit", ".swf":"swf",
        ".tar":"tar", ".tgz":"tgz", ".tiff":"tiff", ".ttc":"ttc", ".ttf":"ttf", ".txt":"txt",
        ".vbs":"vbs",
        ".wav":"wav", ".wma":"wma", ".wmf":"wmf", ".wmv":"wmv", ".wri":"wri",
        ".xls":"xls", ".xlsx":"xlsx", ".xml":"xml",
        ".zip":"zip"
    };
    $scope.path = $location.path();
    $scope.path_elements = [];
    $scope.q = null;
    $scope.limit = 20;
    $scope.search = null;
    $scope.result = null;

    $scope.timer = null;
    
    $scope.dir = {};

    $scope.load = function(path) {
        $scope.path_elements = $scope.split_path(path);
        $scope.info = info.get({path:$scope.path}, function() {}, function() { $scope.info = {error:true} });
        dir.get({path:$scope.path}, function(result) {
            $scope.dir = result;
            $scope.dir.page = 1;
        });
    }

    $scope.load($scope.path);

    function exec_search(path, q, limit, page) {
        var offset = (page - 1) * limit;
        $scope.search = search.get({path:path,q:q,offset:offset,limit:limit}, function(result) {
            if ($scope.q && $scope.q != "") {
                $scope.result = result;
                $scope.result.page = page;
                $scope.thereAreDeletedFiles = false;
                angular.forEach(result.rows, function(row) {
                    if (!row.exists) $scope.thereAreDeletedFiles = true;
                })
            }
        }, function() {
            s = { error:true }
        });
    }

    $scope.$watchCollection("[path, q, limit]", function(newValues,oldValues) {
        var path = newValues[0];
        var oldpath = oldValues[0]
        var q = newValues[1];
        var oldq = oldValues[1];
        var limit = newValues[2];
        if ($scope.timer) {
            $timeout.cancel($scope.timer);
            $scope.timer = null;
        }
        if (path !== oldpath) { // pathが変わった場合はinfo, dirもリロード
            $scope.load(path);
        }
        if ($scope.result) {
            $scope.result.page = 1;
        }
        if (q) {
            if (q === oldq) {// qが一緒でpathやlimitが変わっただけなら即時に検索
                exec_search(path, q, limit, 1);
            } else {
                $scope.timer = $timeout(function() {
                    exec_search(path,q, limit, 1);
                }, $scope.search && $scope.search.$resolved === false? 500 : 100); // 既に検索が走っていれば500ms, フリーなら100ms
            }
        }
        else {
            $scope.search = null;
            $scope.result = null;
        }
    });

    $scope.pageChanged = function() {
        exec_search($scope.path, $scope.q, $scope.limit, $scope.result.page);
    }

    $scope.dirPageChanged = function() {
        var offset = ($scope.dir.page - 1) * $scope.dir.limit;
        dir.get({path:$scope.path, offset:offset},function(result) {
            $scope.dir.count = result.count;
            $scope.dir.limit = result.limit;
            $scope.dir.rows = result.rows;
        });
    }
    
    $scope.filetype = function(row) {
        if (row.size < 0) return "folder";
        var name = row.name;
        var re = /(?:\.([^.]+))?$/;
        var suffix = re.exec(name)[0];
        if (suffix) suffix = suffix.toLowerCase();
        if (!suffix || !filetypes.hasOwnProperty(suffix)) return null;
        return filetypes[suffix];
    }

    $scope.$on('$locationChangeSuccess', function() {
        $scope.path = $location.path();
    });

    $scope.move_to = function(path) {
        if (path == "..") {
            path_spl = $scope.split_path(path);
            if (path_spl.length > 0) {
                path_spl.length = path_spl.length - 1;
            }
            path = path_spl.join("/");
        }
        $location.path(path);
    }

    $scope.open_file = function(path, name) {
        window.open($scope.join_path('.',$scope.join_path(path, name)));
    }

}])
.controller("ShareAdminController", ["$scope","$resource","$filter","messageBox","progressBar", 
                                function($scope, $resource,$filter,messageBox,progressBar) {
    var share = $resource("./share/:name/:action");
    var testSyncOrigin = $resource("./test_sync_origin");
    var formatDate = $filter("date");

    $scope.load_shares = function() {
        $scope.shares = share.query({}, function() {
            $scope.new_share_selected();
        });
    }
    
    $scope.users = [{id:"shimarin",text:"shimarin"},{id:"sorimashi",text:"sorimashi"},{id:"hoge",text:"hoge"}];  // TODO: load
    $scope.groups = [{id:"executive",text:"executive"},{id:"staff",text:"staff"},{id:"guest",text:"guest"}]; // TODO: load
    
    $scope.new_share_selected = function() {
        $scope.share = {new:true,options:{synctime:new Date(1970,1,1,00,00,00)}};
        $scope.valid_users = [];
        $scope.valid_groups = [];
    }
    $scope.share_selected = function(share_name) {
        $scope.share = share.get({name:share_name}, function(result) {
            if (result.options.synctime) {
                var time = result.options.synctime.split(':');
                $scope.share.options.synctime = new Date(1970,1,1,parseInt(time[0]),parseInt(time[1]),00)
            } else {
                $scope.share.options.synctime = new Date(1970,1,1,00,00,00);
            }
            $scope.valid_users = []; // TODO: read from result
            $scope.valid_groups = []; // TODO: read from result
            $scope.shareForm.$setPristine();
            $scope.share.log = share.get({name:share_name,action:"log"})
        });
    }
    $scope.create_share = function() {
        $scope.share.errorMessage = null;
        // TODO: show progress modal to disable user operations
        var params = {
            comment: $scope.share.comment,
            options: {
                syncorigin: $scope.share.options.syncorigin,
                syncday: $scope.share.options.syncday,
                synctime: formatDate($scope.share.options.synctime, "HH:mm")
            }
        };
        var pb = progressBar("新しい共有フォルダを作成中...")
        share.save({name:$scope.share.name,action:"create"},params, function(result) {
            pb.close();
            if (result.success) {
                $scope.load_shares();
            } else {
                $scope.share.errorMessage = result.info;
            }
        }, function() {
            pb.close()
            messageBox("通信エラー", {danger:true});
        });
    }
    $scope.update_share = function() {
        $scope.share.errorMessage = null;
        var params = {
                comment: $scope.share.comment,
                options: {
                    syncorigin: $scope.share.options.syncorigin,
                    syncday: $scope.share.options.syncday,
                    synctime: formatDate($scope.share.options.synctime, "HH:mm")
                }
            };
        share.save({name:$scope.share.name,action:"update"},params, function(result) {
            if (result.success) {
                $scope.load_shares();
            } else {
                $scope.share.errorMessage = result.info;
            }
        });
    }
    $scope.delete_share = function() {
        messageBox("共有フォルダ " + $scope.share.name + " を本当に削除しますか?共有フォルダのファイルは全て削除され、元に戻すことはできません。",
                {danger:true, cancel:true}, function() {
                    var pb = progressBar("共有フォルダを削除中...（時間を要することがあります）")
                    share.delete({name:$scope.share.name}, {}, function(result) {
                        pb.close();
                        if (result.success) {
                            $scope.load_shares();
                        } else {
                            $scope.share.opErrorMessage = result.info;
                        }
                    }, function() {
                        pb.close()
                        messageBox("通信エラー", {danger:true});
                    })
                });
    }
    $scope.truncate_share_index = function() {
        messageBox("共有フォルダ " + $scope.share.name + " の検索インデックスをリセットしますか?(時間を置いて自動的に再作成されます)", {danger:true, cancel:true}, function() {
            var pb = progressBar("検索インデックスをリセット中...");
            share.save({name:$scope.share.name,action:"truncate"}, {}, function(result) {
                pb.close();
                if (result.success) {
                    messageBox("共有フォルダ " + $scope.share.name + " の検索インデックスがリセットされました。");
                } else {
                    $scope.share.opErrorMessage = result.info;
                }
            }, function() {
                pb.close()
                messageBox("通信エラー", {danger:true});
            });
        });
        
    }
    $scope.testSyncOrigin = function() {
        var pb = progressBar("同期元への接続をテスト中...");
        testSyncOrigin.get({
            path:$scope.share.options.syncorigin.path,
            username:$scope.share.options.syncorigin.username,
            password:$scope.share.options.syncorigin.password},
            function(result) {
                pb.close()
                if (result.success) {
                    messageBox("同期元への接続テストに成功しました。");
                } else {
                    var reason = {
                        256: "不明なホスト名",
                        8192: "存在しないホスト又は共有フォルダ"
                    }
                    var reasonStr = reason.hasOwnProperty(result.info)? reason[result.info] : ("" + result.info);
                    messageBox("同期元への接続テストに失敗しました。(" + reasonStr + ")", {danger:true});
                }
            }, function() {
                pb.close()
                messageBox("通信エラー", {danger:true});
            });
    }
    $scope.load_shares();
}])
.controller("UserAdminController", ["$scope","$resource","$filter","messageBox","progressBar", 
                                function($scope, $resource,$filter,messageBox,progressBar) {
    var user = $resource("./user/:name/:action");
    $scope.load_users = function() {
        $scope.users = user.query({}, function() {
            $scope.new_user_selected();
        });
    }
    
    $scope.new_user_selected = function() {
        $scope.user = {new:true,admin:false};
    }
    $scope.user_selected = function(user_name) {
        $scope.user = user.get({name:user_name}, function() {
            $scope.userForm.$setPristine();
        });
    }
    
    $scope.create_user = function() {
        user.save({name:$scope.user.name, action:"create"}, {admin:$scope.user.admin,password:$scope.user.password}, function(result) {
            if (result.success) {
                $scope.load_users();
            } else {
                $scope.user.errorMessage = result.info;
            }
        });
    }
    $scope.update_user = function() {
        user.save({name:$scope.user.name, action:"update"}, {admin:$scope.user.admin,password:$scope.user.password}, function(result) {
            if (result.success) {
                $scope.load_users();
            } else {
                $scope.user.errorMessage = result.info;
            }
        });
    }
    $scope.delete_user = function() {
        messageBox("ユーザー " + $scope.user.name + " を本当に削除しますか?",{danger:true, cancel:true}, function() {
            user.delete({name:$scope.user.name}, {}, function(result) {
                if (result.success) {
                    $scope.load_users();
                } else {
                    $scope.user.opErrorMessage = result.info;
                }
            })
        });
    }
    
    $scope.load_users();
}])
.controller("EtcAdminController", ["$scope","$resource","$upload", "messageBox","progressBar", 
                                function($scope, $resource,$upload, messageBox,progressBar) {
    $scope.message = "開発元から提供されているアップデートファイルを選択してください。"
    $scope.onFileSelect = function($files) {
        for (var i = 0; i < $files.length && i < 1; i++) {
            var file = $files[i];
            var pb = progressBar("アップデートを実行中...");
            $scope.upload = $upload.upload({
               "url":"update",
               file: file,
            }).success(function(data, status, headers, config) {
                pb.close()
                if (data.success) {
                    $scope.message = "アップデート完了";
                    if (data.info) {
                        $scope.message += ": " + data.info;
                    }
                } else {
                    $scope.message = "アップデート失敗: " + data.info
                }
            }).error(function() {
                pb.close()
                console.log("通信エラーが発生しました");
            });
        }
    }
}])
.directive('focus', ["$timeout", function($timeout) {
    return {
        scope : {
            trigger : '@focus'
        },
        link : function(scope, element) {
            scope.$watch('trigger', function(value) {
                if (value === "true") {
                    $timeout(function() {
                        element[0].focus();
                    }, 200);
                }
            });
        }
    };
}])
.directive("match", ["$parse", function($parse) {
    return {
        require: 'ngModel',
        link: function(scope, elem, attrs, ctrl) {
            scope.$watch(function() {
                var target = $parse(attrs.match)(scope);  // 比較対象となるモデルの値
                return !ctrl.$modelValue || target === ctrl.$modelValue;
            }, function(currentValue) {
                ctrl.$setValidity('mismatch', currentValue);
            });
        }
    }
}])
.directive("folderName", function() {
    function isvalid(value) {
        return !/[\\\/\:\;\|\,\*\?\<\>\"\']/.test(value);
    }
    return {
        restrict: 'A',
        require: 'ngModel',
        link: function(scope, elem, attr, ctrl) {
            ctrl.$parsers.push(function(value) {
                if (!/[\\\/\:\;\|\,\*\?\<\>\"\']/.test(value)) {
                    ctrl.$setValidity("folderName", true);
                    return value;
                } else {
                    ctrl.$setValidity("folderName", false)
                    return undefined;
                }
            })
        }
    }
})
.factory("messageBox", ["$rootScope","$modal", function($rootScope, $modal) {
    return function(message, options, callback) {
       var $scope = $rootScope.$new();
       $scope.message = message;
       $scope.options = options;
       $modal.open(
           {
               templateUrl:"messagebox.html", 
               scope: $scope
           }
       ).result.then(function (result) { 
           if (typeof callback === "undefined") return;
           callback(result);
       });
    }
}])
.factory("progressBar", ["$rootScope","$modal", function($rootScope, $modal) {
    return function(message) {
        var $scope = $rootScope.$new();
        $scope.message = message;
        return $modal.open({
            templateUrl:"progressbar.html",
            scope: $scope,
            backdrop:"static",keyboard:false// ユーザーがクローズできないようにする
        });
    }
}])
.run(["$rootScope","$location", "$modal", function($scope,$location,$modal) {
    $scope.Math = window.Math;
    $scope.about = function() {
        $modal.open({
            templateUrl:"about.html"
        });
    }
    $scope.iehelp = function() {
        $modal.open({
            templateUrl:"iehelp.html"
        });
    }
    $scope.eden_link = function(share, path, name) {
        var link = "file://///" + $location.host();
        if (share) {
            link = $scope.join_path(link, share);
            if (path) {
                link = $scope.join_path(link, path);
                if (name) {
                    link = $scope.join_path(link, name);
                }
            }
        }
        return link;
    }
    $scope.join_path = function(path1, path2) {
        path1 = path1.replace(/\/+$/, "");
        path2 = path2.replace(/^\/+/, "");
        return path1 + "/" + path2;
    }
    $scope.split_path = function(path) {
        path = path.replace(/\/+$/, "");
        path = path.replace(/^\/+/, "");
        if (path == "") return [];
        return path.split("/");
    }
}])
