
function DisplayTS(h,CurrentDate, CurrentTime, Scope, EventsDayRadars, BoundariesRadar, IDsRadar, PhasesDay, BoundariesPhases, Bulk)

%% Defining parameters and the physics of the model (Sensors from the file loaded below)
% load('G:\TSC\Grants\G2015_Multimodal_Safety_Dynamics\Analysis\RadarsProperties');
load('RadarsProperties');
ZoneShape = Sensors{6};
   
%% Plot TS diagram
    figure(h);
    %subplot(4,3,4,'Position',[.03 .05 .38 .5]);
    subplot('Position',[.05 .05 .4 .5]);
    cla();
%     for i = [1,2,4,5,6,8,13,14,15,16]
%     BoundariesPhases
    for i = [1,2,4,5,6,8,14]
%         disp(i)
        for j = BoundariesPhases(i,1):BoundariesPhases(i,2)
            hold on;

            
            rectangle('Position',[PhasesDay(i).TimeDetect(j)-CurrentTime 80+i PhasesDay(i).TimeUndetect(j)-PhasesDay(i).TimeDetect(j) 1],...
                'FaceColor',[0 1 0]);
            hold on;
            text(PhasesDay(i).TimeDetect(j)-CurrentTime, 80+i+3, ['phase ' num2str(i)] );
        end
    end
    
    disp('End of Boundary Phases');
%     BoundariesRadar

    for i = 1:length(IDsRadar) 
%         disp(i)
        index = find(strcmp( IDsRadar(i), Sensors{1}));
        if (BoundariesRadar(i,1)>0) && (BoundariesRadar(i,1) <= BoundariesRadar(i,2))
            range = [BoundariesRadar(i,1):BoundariesRadar(i,2)];
            x1 = arrayfun(@(j) (EventsDayRadars(i).TimeDetect(j)-CurrentTime),range);
            x2 = arrayfun(@(j) (EventsDayRadars(i).TimeUndetect(j)-CurrentTime),range);
            y = repmat(Sensors{5}{index}(2), 2,length(range));
            x = [x1;x2;];
            
            if Bulk==0
                plot(x,y,'Color','blue');
            else
                for j = BoundariesRadar(i,1):BoundariesRadar(i,2)
                    
                    hold on;
                    plot([EventsDayRadars(i).TimeDetect(j)-CurrentTime EventsDayRadars(i).TimeUndetect(j)-CurrentTime], [Sensors{5}{index}(2) Sensors{5}{index}(2)], ...
                            'LineWidth',(EventsDayRadars(i).BulkMax(j)-128)/2,'Color','blue');
%                     else
%                         plot([EventsDayRadars(i).TimeDetect(j)-CurrentTime EventsDayRadars(i).TimeUndetect(j)-CurrentTime], [Sensors{5}{index}(2) Sensors{5}{index}(2)]);
%                     end
                end
        end
        
    end
    
    
    xlabel('time t');
    ylabel('y position');
    
    text(-10,105,datestr(CurrentDate));
    ss = mod(CurrentTime,86400);
    h = floor(ss/3600);
    m = floor((ss - h*3600)/60);
    s = ss - h*3600-60*m;
    text(0,105,[num2str(h), ' h ', num2str(m),' m ',num2str(s), ' s']);
    xlim([-Scope/2, Scope/2]);
    ylim([-10 100]);
    
    
    
    
    
end