function Interface_data_collection(IDsRadar,IDsMag)
    
    global h Year Month Day Hour Min Sec CurrentDate CurrentTime EpochTimeStamp datenumEpoch FPS Speed Scope EventsDayMag EventsDayRadars EventsDayRadars2 BoundariesMag BoundariesRadar play ...
        PhasesDay BoundariesPhases Bulk hough Merged ListFavorite vidObj oldt filen uihand;
    uihand=zeros(13,1);
    EventsDayRadars2=[];
    %load('G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\ListMagSensors.mat');
    %load('G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\PedData\ListMicroRadars.mat');
    
%     Months = {'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'};
%     Days = {'01', '02', '03', '04', '05', '06', '07', '08', '09', '10', ...
%         '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', ...
%         '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31'};
%     Hours = {'00','01', '02', '03', '04', '05', '06', '07', '08', '09', '10', ...
%         '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', ...
%         '21', '22', '23'};
%     MinsSecs = {'00','01', '02', '03', '04', '05', '06', '07', '08', '09', '10', ...
%         '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', ...
%         '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',...
%         '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', ...
%         '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', ...
%         '51', '52', '53', '54', '55', '56', '57', '58', '59'};
    
%     Months = {'04'};
%     Days = {'22', '23', '24'};
    Months = {'04'};
    Days = {'22'};
%     daysint= [12];
    Hours = {'00','01', '02', '03', '04', '05', '06', '07', '08', '09', '10', ...
        '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', ...
        '21', '22', '23'};
    MinsSecs = {'00','01', '02', '03', '04', '05', '06', '07', '08', '09', '10', ...
        '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', ...
        '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',...
        '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', ...
        '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', ...
        '51', '52', '53', '54', '55', '56', '57', '58', '59'};

    ImagePosition=[100 50 1500 950];
    PlotPosition=[100 50 1000 400];
    h = figure('Position', ImagePosition, 'color','w');
    vidObj=[];
    oldt=0;
    CommandPosition = [1000 700 60 40];
    
    EpochTimeStamp = 1356998400; % seconds at reference datenumEpoch
    datenumEpoch = datenum(2013,1,1);

    ListFavorite = [];
    
    Year = 2015;
    Month = 04;
    Day = 22;
    Hour = 06;
    Min = 30;
    Sec = 00;

%     Year = 2014;
%     Month = 01;
%     Day = 01;
%     Hour = 12;
%     Min = 00;
%     Sec = 00;

    
    
    CurrentDate = datenum(Year,Month,Day);
    CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec;

    FPS = 8.0;
    Speed = 8.0;
    Scope = 60.0; % time frame in seconds
    Bulk = 1;
    Merged = 1;
        
    function Refresh
        %disp('youhouu');
        %disp(datestr(now,'mmmm dd, yyyy HH:MM:SS.FFF'));
        disp(CurrentDate);
        disp(num2str(CurrentTime));
        [EventsDayMag, EventsDayRadars,EventsDayRadars2, PhasesDay, BoundariesPhases, BoundariesRadar, BoundariesMag,filen] = GetData_TimeDay_add(CurrentDate, CurrentTime, Scope, IDsRadar, IDsMag, Merged);
         disp('End of GetData_TimeDay');
        %disp(datestr(now,'mmmm dd, yyyy HH:MM:SS.FFF'));
        DisplayTS(h,CurrentDate, CurrentTime, Scope, EventsDayRadars, BoundariesRadar,  IDsRadar, PhasesDay, BoundariesPhases, Bulk);
        disp('End of DisplayTS');
        %disp(datestr(now,'mmmm dd, yyyy HH:MM:SS.FFF'));
        DisplayMap_add(h, BoundariesRadar, IDsRadar, EventsDayRadars);
        disp('End of DisplayMap');
        %disp(datestr(now,'mmmm dd, yyyy HH:MM:SS.FFF'));
        DisplayMags(h, CurrentDate, CurrentTime, Scope, EventsDayMag, BoundariesMag, IDsMag, PhasesDay, BoundariesPhases);
         disp('End of DisplayMags');
        %disp(datestr(now,'mmmm dd, yyyy HH:MM:SS.FFF'));
        [vidObj]=DisplayVideoOct(h, vidObj, oldt, CurrentDate, CurrentTime, EventsDayRadars, BoundariesRadar, ...
    PhasesDay,BoundariesPhases, EventsDayMag, BoundariesMag, IDsRadar, IDsMag);

        
    end

    tic
    Refresh;
    
    %% set date and time buttons
    uicontrol(h, 'Style','text','String','Month','Position',CommandPosition+[0 170 0 0]);
    SetMonthBtn = uicontrol(h, 'Style','popup','String',Months,'Position',CommandPosition+[0 150 0 0],...
        'Callback',@SetMonth);
    uicontrol(h, 'Style','text','String','Day','Position',CommandPosition+[65 170 0 0]);
    SetDayBtn = uicontrol(h, 'Style','popup','String',Days,'Position',CommandPosition+[65 150 0 0],...
         'Callback',@SetDay);
    uicontrol(h, 'Style','text','String','Hour','Position',CommandPosition+[0 120 0 0]);
    SetHourBtn = uicontrol(h, 'Style','popup','String',Hours,'Value',Hour+1,'Position',CommandPosition+[0 100 0 0],...
        'Callback',@SetHour);
    uicontrol(h, 'Style','text','String','Minute','Position',CommandPosition+[65 120 0 0]);
    SetMinBtn = uicontrol(h, 'Style','popup','String',MinsSecs,'Value',Min+1,'Position',CommandPosition+[65 100 0 0],...
        'Callback',@SetMin);
    uicontrol(h, 'Style','text','String','Second','Position',CommandPosition+[130 120 0 0]);
    SetSecBtn = uicontrol(h, 'Style','popup','String',MinsSecs,'Value',Sec+1,'Position',CommandPosition+[130 100 0 0],...
        'Callback',@SetSec);
    
    uicontrol(h, 'Style','text','String',['Scale ' num2str(Scope)],'Position',CommandPosition+[200 40 0 -20]);
    SetScopeBtn = uicontrol(h, 'Style','slider','Min',10,'Max',60,'Value',30,'Position',CommandPosition+[200 0 0 0],...
        'Callback',@SetScope);
    
    uicontrol(h, 'Style','text','String','FPS','Position',CommandPosition+[195 170 0 0]);
    SetFPSbtn = uicontrol(h, 'Style','popup','String',{'1','2','4','8'}, 'Value',4,'Position',CommandPosition+[195 150 0 0],... 
        'Callback',@SetFPS);
    uicontrol(h, 'Style','text','String','Speed','Position',CommandPosition+[260 170 0 0]);
    SetSpeedbtn = uicontrol(h, 'Style','popup','String',{'1','2','4','8'}, 'Value',4, 'Position',CommandPosition+[260 150 0 0],... 
        'Callback',@SetSpeed);
    
    %uicontrol(h, 'Style','text','String','Bulk', 'Position',CommandPosition + [265 170 0 0]);
    BulkBtn = uicontrol(h, 'Style','checkbox','String','Display Bulk','Value',1,'Position',CommandPosition + [325 170 40 0],...
        'Callback',@SetBulk);
    
    MergedBtn = uicontrol(h, 'Style','checkbox', 'String', 'Merge Events','Value',1,'Position',CommandPosition + [325 130 40 0],...
        'Callback',@SetMerged);
    
    HoughBtn = uicontrol(h, 'Style','checkbox','String','Show Hough Estimates','Value',1,'Position',CommandPosition + [325 90 40 0],...
        'Callback',@SetHough);
    
%     FavoriteBtn = uicontrol(h, 'Style','pushbutton','String','Add View to Favorites List','Position',CommandPosition+[325 50 40 0], ...
%          'Callback', @AddFavorite);
%     SaveFavBtn = uicontrol(h, 'Style','pushbutton','String','Save Favorites List','Position',CommandPosition+[325 0 40 0], ...
%          'Callback', @SaveFavorites);
%     LoadFavBtn = uicontrol(h, 'Style','pushbutton','String','Load Favorites List','Position',CommandPosition+[325 -50 40 0], ...
%          'Callback', @LoadFavorites);
        
    function SetMonth(source, callbackdata)
        Month = get(source,'Value');
        CurrentDate = datenum(Year, Month, Day);
        CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec;
        Refresh;
    end
    function SetDay(source, callbackdata)
        Day = daysint(get(source,'Value'));
        CurrentDate = datenum(Year, Month, Day);
        CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec;
        Refresh;
    end
    function SetHour(source,callbackdata)
        Hour = get(source,'Value')-1;
        CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec; 
        Refresh;
    end
    function SetMin(source,callbackdata)
        Min = get(source,'Value')-1;
        CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec; 
        Refresh;
    end
    function SetSec(source,callbackdata)
        Sec = get(source,'Value')-1;
        CurrentTime = EpochTimeStamp + (CurrentDate - datenumEpoch) * 86400 + 3600*Hour + 60*Min + Sec; 
        Refresh;
    end
    
    function SetScope(source,callbackdata)
        Scope = get(source,'Value');
        uicontrol(h, 'Style','text','String',['Scale ' num2str(Scope)],'Position',CommandPosition+[200 40 0 -20]);
        Refresh;
    end

    function SetFPS(source, callbackdata)
        FPS = 2^(get(source,'Value')-1);
    end
    function SetSpeed(source, callbackdata)
        Speed = 2^(get(source,'Value')-1);
    end
    function SetBulk(source, callbackdata)
        Bulk = get(source,'Value');
        Refresh;
    end
    function SetMerged(source, callbackdata)
        Merged = get(source,'Value');
        Refresh;
    end
%     function SetHough(source, callbackdata)
%         hough = get(source,'Value');
%         figure(h);
%         cla(subplot('Position',[.05 .05 .4 .5]));
%         Refresh;
%     end

%     function AddFavorite(source, callbackdata)
%         ListFavorite = [ListFavorite; CurrentTime];
%     end
% 
%     function SaveFavorites(source, callbackdata)
%         ToSave = ListFavorite;
%         uisave('ToSave', 'MyFavoriteDates');
%         ListFavorite = [];
%     end
% 
%     function LoadFavorites(source,callbackdata)
%         uiopen();
%     end
%% pause and play buttons
    ForwardBtn = uicontrol(h, 'Style','pushbutton','String','Forward','Position',CommandPosition+[65 50 0 0], ...
         'Callback', @Forward);
    BackwardBtn = uicontrol(h, 'Style','pushbutton','String','Backward', 'Position',CommandPosition+[0 50 0 0] ,...
         'Callback', @Backward);

    PlayBtn = uicontrol(h, 'Style', 'togglebutton','String','Play','Position',CommandPosition,...
         'Callback', @Play);
 %   PauseBtn = uicontrol(h, 'Style', 'togglebutton','String','Pause','Position',CommandPosition+[65 0 0 0],...
 %        'Callback', 'play = false;');

    
    function Forward(source,callbackdata)
        oldt=CurrentTime;
        CurrentTime = CurrentTime + 1/FPS;
        Refresh;
    end

    function Backward(source,callbackdata)
        oldt=CurrentTime;
        CurrentTime = CurrentTime - 1/FPS;
        Refresh;
    end

    function Play(source,callbackdata)
        play = get(source,'Value');
        while (play == get(source,'Max')) && (CurrentTime < EpochTimeStamp + (CurrentDate - datenumEpoch + 1) * 86400)
            oldt=CurrentTime;
            CurrentTime = CurrentTime + 1/FPS;
            Refresh;
            pause(1/FPS/Speed);
        end
    end
 

end
